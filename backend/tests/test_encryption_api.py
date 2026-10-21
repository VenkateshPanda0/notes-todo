import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.db import crypto, manager as manager_module
from backend.app.db.manager import manager
from backend.app.main import app

pytestmark = pytest.mark.skipif(not crypto.AVAILABLE, reason="sqlcipher3 is not installed")

PASSWORD = "correct horse"
MARKER = "ENCRYPTION-TEST-MARKER-7c1e"


class Env:
    """A real database file managed by the real manager (no dependency overrides), plus helpers."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.path = directory / "flow.db"
        self.url = f"sqlite:///{self.path}"
        self.client: TestClient | None = None
        self.token: str | None = None

    # -- requests -------------------------------------------------------------------------------
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get(self, path, **kw):
        return self.client.get(path, headers=self.headers(), **kw)

    def post(self, path, json=None, **kw):
        return self.client.post(path, json=json, headers=self.headers(), **kw)

    def make(self, title, content=""):
        r = self.post("/api/items", {"title": title, "type": "NOTE", "content": content})
        assert r.status_code == 201, r.text
        return r.json()

    def titles(self):
        r = self.get("/api/items")
        assert r.status_code == 200, r.text
        return sorted(i["title"] for i in r.json())

    # -- flows ----------------------------------------------------------------------------------
    def set_password(self, password=PASSWORD):
        r = self.client.post("/api/auth/setup", json={"password": password})
        assert r.status_code == 200, r.text
        self.token = r.json()["token"]

    def enable(self, password=PASSWORD):
        return self.post("/api/auth/encryption/enable", {"password": password})

    def disable(self, password=PASSWORD):
        return self.post("/api/auth/encryption/disable", {"password": password})

    def unlock(self, password=PASSWORD):
        r = self.client.post("/api/auth/unlock", json={"password": password})
        if r.status_code == 200:
            self.token = r.json()["token"]
        return r

    def status(self):
        return self.client.get("/api/auth/status").json()

    def restart(self):
        """Simulate quitting and relaunching the app: a new process sees only what is on disk."""
        manager.close()
        manager.configure(self.url)
        manager.start()
        self.token = None  # session tokens live in memory only

    @property
    def raw(self) -> bytes:
        return self.path.read_bytes()

    def plain_header(self) -> bool:
        return self.raw[:16] == b"SQLite format 3\x00"


@pytest.fixture()
def env(tmp_path):
    original = manager.url
    environment = Env(tmp_path)
    manager.configure(environment.url)
    app.dependency_overrides.clear()
    with TestClient(app) as client:  # startup runs manager.start(): schema is created
        environment.client = client
        yield environment
    manager.close()
    manager.configure(original)


@pytest.fixture()
def encrypted(env):
    """An encrypted database containing three notes, with the session still open."""
    env.make(MARKER + " one", "body one")
    env.make("two", "body two")
    env.make("three")
    env.set_password()
    assert env.enable().status_code == 200
    return env


# --- status and prerequisites --------------------------------------------------------------------


def test_a_new_database_is_plain_and_offers_encryption(env):
    status = env.status()

    assert status == {"is_locked": False, "encrypted": False, "encryption_available": True}
    assert env.plain_header()


def test_encryption_needs_an_app_lock_password_first(env):
    response = env.post("/api/auth/encryption/enable", {"password": PASSWORD})

    assert response.status_code == 409 and "App Lock password" in response.json()["detail"]
    assert env.plain_header()


def test_a_wrong_password_does_not_encrypt(env):
    env.set_password()

    response = env.enable("not-the-password")

    assert response.status_code == 401
    assert env.plain_header() and env.status()["encrypted"] is False


def test_enabling_is_rate_limited_like_unlocking(env):
    env.set_password()
    for _ in range(5):
        assert env.enable("nope-nope").status_code == 401

    assert env.enable("nope-nope").status_code == 429
    assert env.enable().status_code == 429  # even the right password waits out the lockout


def test_encryption_unavailable_is_reported_not_crashed(env, monkeypatch):
    env.set_password()
    monkeypatch.setattr(manager_module.crypto, "AVAILABLE", False)

    assert env.status()["encryption_available"] is False
    assert env.enable().status_code == 409


# --- enabling ------------------------------------------------------------------------------------


def test_enabling_encrypts_the_file_and_keeps_the_session_working(encrypted):
    raw = encrypted.raw

    assert not encrypted.plain_header()
    assert MARKER.encode() not in raw and b"CREATE TABLE" not in raw
    assert encrypted.status()["encrypted"] is True
    assert encrypted.titles() == [MARKER + " one", "three", "two"]  # same token still works, data intact
    assert not Path(str(encrypted.path) + ".unencrypted").exists()
    assert not Path(str(encrypted.path) + ".encrypting").exists()
    assert encrypted.make("added after encryption")["title"] == "added after encryption"


def test_enabling_twice_is_refused(encrypted):
    assert encrypted.enable().status_code == 409


def test_new_writes_after_encryption_are_encrypted_too(encrypted):
    encrypted.make(MARKER + " written later")

    assert MARKER.encode() not in encrypted.raw


# --- restart, lock, unlock -----------------------------------------------------------------------


def test_after_a_restart_nothing_is_readable_until_the_password_is_entered(encrypted):
    encrypted.restart()

    assert encrypted.status() == {"is_locked": True, "encrypted": True, "encryption_available": True}
    for path in ("/api/items", "/api/tags", "/api/graph", "/api/backup/export.json", "/api/ai/status"):
        assert encrypted.client.get(path).status_code == 401, path
    assert manager.is_open is False


def test_unlocking_with_the_password_opens_the_database_with_everything_in_it(encrypted):
    encrypted.restart()

    assert encrypted.unlock("wrong").status_code == 401
    assert manager.is_open is False
    assert encrypted.unlock().status_code == 200

    assert encrypted.titles() == [MARKER + " one", "three", "two"]
    assert encrypted.status()["encrypted"] is True


def test_a_wrong_password_never_opens_it_and_counts_toward_the_lockout(encrypted):
    encrypted.restart()
    for _ in range(5):
        assert encrypted.unlock("guess-guess").status_code == 401

    assert encrypted.unlock().status_code == 429  # locked out, even with the right password
    assert manager.is_open is False


def test_lock_now_closes_the_database_and_forgets_the_key(encrypted):
    response = encrypted.post("/api/auth/lock")

    assert response.status_code == 204
    assert manager.is_open is False and manager._password is None
    assert encrypted.get("/api/items").status_code == 401
    assert encrypted.status()["is_locked"] is True
    assert encrypted.unlock().status_code == 200 and len(encrypted.titles()) == 3


def test_lock_now_on_a_plain_database_keeps_it_open(env):
    env.set_password()
    env.post("/api/auth/lock")

    assert manager.is_open is True and env.status()["is_locked"] is True


def test_unlock_runs_pending_schema_upgrades_on_the_encrypted_file(tmp_path):
    """An encrypted database written by an older release must be upgraded after unlocking."""
    import sqlite3 as stdlib

    legacy = tmp_path / "old.db"
    connection = stdlib.connect(legacy)
    connection.executescript(
        "CREATE TABLE items (id INTEGER NOT NULL PRIMARY KEY, title VARCHAR(255) NOT NULL, content TEXT NOT NULL,"
        " type VARCHAR(4) NOT NULL, completed BOOLEAN NOT NULL, priority VARCHAR(6) NOT NULL, due_date DATE,"
        " created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL);"
        "CREATE TABLE app_settings (id INTEGER NOT NULL PRIMARY KEY, password_hash VARCHAR(255) NOT NULL);"
        "INSERT INTO items VALUES (1,'Old','x','NOTE',0,'LOW',NULL,'2026-01-01 00:00:00','2026-01-01 00:00:00');"
    )
    connection.commit()
    connection.close()
    target = tmp_path / "flow.db"
    crypto.convert(legacy, target, None, PASSWORD)
    original = manager.url
    manager.configure(f"sqlite:///{target}")
    try:
        with TestClient(app) as client:
            response = client.post("/api/auth/unlock", json={"password": PASSWORD})
            token = response.json()["token"]
            items = client.get("/api/items", headers={"Authorization": f"Bearer {token}"}).json()
    finally:
        manager.close()
        manager.configure(original)

    assert response.status_code == 200
    assert [i["title"] for i in items] == ["Old"] and items[0]["recurrence"] is None


def test_an_encrypted_database_from_a_newer_app_is_refused_and_stays_closed(tmp_path):
    source = tmp_path / "src.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY)")
    connection.execute("PRAGMA user_version = 99")
    connection.commit()
    connection.close()
    target = tmp_path / "flow.db"
    crypto.convert(source, target, None, PASSWORD)
    original = manager.url
    manager.configure(f"sqlite:///{target}")
    try:
        with TestClient(app) as client:
            response = client.post("/api/auth/unlock", json={"password": PASSWORD})
            still_closed = manager.is_open is False
    finally:
        manager.close()
        manager.configure(original)

    assert response.status_code == 500 and "newer version" in response.json()["detail"]
    assert still_closed


# --- backups -------------------------------------------------------------------------------------


def test_enabling_securely_removes_old_plain_backups_and_makes_an_encrypted_one(env, monkeypatch):
    monkeypatch.delenv("TASKFLOW_DISABLE_AUTO_BACKUP")
    env.make(MARKER)
    env.set_password()
    from backend.app.services.backup import run_auto_backup

    old = run_auto_backup(manager.engine, force=True)
    assert old is not None and MARKER.encode() in old.read_bytes()  # a plain backup exists

    result = env.enable().json()

    backups = sorted((env.dir / "backups").glob("*.db"))
    assert result == {"encrypted": True, "removed_plain_backups": 1}
    assert backups, "a fresh backup must exist"
    for backup in backups:
        assert crypto.is_encrypted_file(backup) and MARKER.encode() not in backup.read_bytes()
        assert crypto.fingerprint_of(backup, PASSWORD)["tables"]["items"] == 1


def test_backups_made_while_encrypted_are_encrypted(encrypted):
    from backend.app.services.backup import run_auto_backup, snapshot_before_import

    daily = run_auto_backup(manager.engine, force=True)
    before_import = snapshot_before_import(manager.engine)

    for path in (daily, before_import):
        assert crypto.is_encrypted_file(path) and MARKER.encode() not in path.read_bytes()


def test_the_database_copy_download_is_encrypted_and_opens_with_the_password(encrypted, tmp_path):
    response = encrypted.get("/api/backup/database")
    copy = tmp_path / "download.db"
    copy.write_bytes(response.content)

    assert response.status_code == 200 and crypto.is_encrypted_file(copy)
    assert crypto.fingerprint_of(copy, PASSWORD)["tables"]["items"] == 3


def test_replace_import_on_an_encrypted_database_keeps_an_encrypted_safety_copy(encrypted):
    payload = {"format": "taskflow-export", "version": 1, "items": [{"title": "fresh", "type": "NOTE"}]}

    response = encrypted.post("/api/backup/import?mode=replace", payload)

    assert response.status_code == 200 and encrypted.titles() == ["fresh"]
    copies = list((encrypted.dir / "backups").glob("before-import-*.db"))
    assert len(copies) == 1 and crypto.is_encrypted_file(copies[0])
    assert crypto.fingerprint_of(copies[0], PASSWORD)["tables"]["items"] == 3


# --- changing the password -----------------------------------------------------------------------


def test_changing_the_password_rekeys_the_database_and_its_backups(encrypted, monkeypatch):
    monkeypatch.delenv("TASKFLOW_DISABLE_AUTO_BACKUP")
    from backend.app.services.backup import run_auto_backup

    backup = run_auto_backup(manager.engine, force=True)

    response = encrypted.post("/api/auth/change-password", {"current_password": PASSWORD, "new_password": "brand new pw"})

    assert response.status_code == 200
    encrypted.token = response.json()["token"]
    assert encrypted.titles() == [MARKER + " one", "three", "two"]  # still open and readable
    assert crypto.fingerprint_of(backup, "brand new pw")["tables"]["items"] == 3  # backups follow the password
    encrypted.restart()
    assert encrypted.unlock(PASSWORD).status_code == 401
    assert encrypted.unlock("brand new pw").status_code == 200
    assert encrypted.titles() == [MARKER + " one", "three", "two"]


def test_a_wrong_current_password_changes_nothing_when_encrypted(encrypted):
    before = encrypted.raw

    response = encrypted.post("/api/auth/change-password", {"current_password": "WRONG", "new_password": "brand new pw"})

    assert response.status_code == 401 and encrypted.raw == before
    encrypted.restart()
    assert encrypted.unlock(PASSWORD).status_code == 200


def test_changing_the_password_ends_other_sessions(encrypted):
    old_token = encrypted.token

    response = encrypted.post("/api/auth/change-password", {"current_password": PASSWORD, "new_password": "brand new pw"})

    assert encrypted.client.get("/api/items", headers={"Authorization": f"Bearer {old_token}"}).status_code == 401
    assert encrypted.client.get("/api/items", headers={"Authorization": f"Bearer {response.json()['token']}"}).status_code == 200


# --- disabling -----------------------------------------------------------------------------------


def test_disabling_returns_a_plain_database_with_all_the_data(encrypted):
    assert encrypted.disable("not-it").status_code == 401
    assert not encrypted.plain_header()  # a wrong password changed nothing

    response = encrypted.disable()

    assert response.status_code == 200 and response.json()["encrypted"] is False
    assert encrypted.plain_header() and MARKER.encode() in encrypted.raw
    assert encrypted.status()["encrypted"] is False
    assert encrypted.titles() == [MARKER + " one", "three", "two"]
    assert not Path(str(encrypted.path) + ".encrypted-old").exists()
    encrypted.restart()
    assert encrypted.status()["is_locked"] is True and encrypted.status()["encrypted"] is False
    assert manager.is_open  # a plain database opens at startup again


def test_disabling_when_not_encrypted_is_refused(env):
    env.set_password()

    assert env.disable().status_code == 409


def test_encryption_can_be_turned_on_again_after_being_turned_off(encrypted):
    encrypted.disable()

    assert encrypted.enable().status_code == 200
    assert not encrypted.plain_header() and len(encrypted.titles()) == 3


# --- failures and crashes: the user's data must survive all of them ------------------------------


def test_a_failure_while_building_the_encrypted_copy_leaves_everything_as_it_was(env, monkeypatch):
    env.make(MARKER)
    env.set_password()
    before = env.raw
    monkeypatch.setattr(manager_module.crypto, "convert", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))

    response = env.enable()

    assert response.status_code == 500 and "data is unchanged" in response.json()["detail"]
    assert env.raw == before and env.plain_header()
    assert env.titles() == [MARKER]  # the app keeps working
    assert not Path(str(env.path) + ".encrypting").exists()


def test_a_failed_verification_after_the_swap_restores_the_plain_original(env, monkeypatch):
    env.make(MARKER)
    env.set_password()
    before = env.raw
    calls = {"n": 0}
    real_verify = crypto.verify

    def flaky_verify(path, password, expected):
        calls["n"] += 1
        if calls["n"] == 2:  # 1: inside convert(); 2: the final check after the swap
            raise crypto.VerificationError("simulated corruption")
        return real_verify(path, password, expected)

    monkeypatch.setattr(manager_module.crypto, "verify", flaky_verify)

    response = env.enable()

    assert response.status_code == 500 and "nothing was changed" in response.json()["detail"]
    assert env.raw == before and env.plain_header() and env.titles() == [MARKER]
    assert env.status()["encrypted"] is False
    for leftover in (".unencrypted", ".encrypting", ".failed-encrypted"):
        assert not Path(str(env.path) + leftover).exists(), leftover


def test_a_crash_between_the_two_renames_is_repaired_on_the_next_start(env):
    """Power loss right after the plain file was moved aside, before the encrypted one moved in."""
    env.make(MARKER)
    env.set_password()
    manager.close()
    Path(env.path).rename(str(env.path) + ".unencrypted")  # the state a crash would leave
    assert not env.path.exists()

    manager.configure(env.url)
    manager.start()

    assert env.path.exists() and not Path(str(env.path) + ".unencrypted").exists()
    assert env.plain_header() and manager.is_open
    env.token = None
    env.unlock()  # lock password survived too
    assert env.titles() == [MARKER]


def test_a_crash_during_decryption_is_repaired_on_the_next_start(encrypted):
    manager.close()
    Path(encrypted.path).rename(str(encrypted.path) + ".encrypted-old")

    manager.configure(encrypted.url)

    assert crypto.is_encrypted_file(encrypted.path) and manager.is_open is False
    assert encrypted.unlock().status_code == 200 and len(encrypted.titles()) == 3


def test_unfinished_work_files_are_discarded_at_startup(env):
    env.set_password()
    for suffix in (".encrypting", ".decrypting", ".rekey-backup"):
        Path(str(env.path) + suffix).write_bytes(b"half written")

    env.make("kept")
    env.restart()

    for suffix in (".encrypting", ".decrypting", ".rekey-backup"):
        assert not Path(str(env.path) + suffix).exists()
    assert env.unlock().status_code == 200  # the lock password survived the restart
    assert env.titles() == ["kept"]  # and the main database is untouched


def test_a_leftover_plain_original_is_wiped_once_the_encrypted_file_has_opened(encrypted):
    leftover = Path(str(encrypted.path) + ".unencrypted")
    leftover.write_bytes(MARKER.encode() * 100)  # as if cleanup had been interrupted
    encrypted.restart()

    assert leftover.exists()  # not touched until the encrypted file is proven to open
    encrypted.unlock()

    assert not leftover.exists()


def test_busy_database_makes_the_switch_wait_then_give_up_without_changing_anything(env, monkeypatch):
    env.make(MARKER)
    env.set_password()
    before = env.raw
    monkeypatch.setattr(manager_module, "EXCLUSIVE_TIMEOUT", 0.3)
    held = manager.engine.connect()  # an in-flight request holding a connection
    try:
        response = env.enable()
    finally:
        held.close()

    assert response.status_code == 503
    assert env.raw == before and env.plain_header()
    assert env.titles() == [MARKER]


def test_requests_during_a_switch_get_a_503_not_a_crash(env):
    env.set_password()
    manager._maintenance = True
    try:
        response = env.get("/api/items")
    finally:
        manager._maintenance = False

    assert response.status_code == 503 and "busy" in response.json()["detail"].lower()


# --- concurrency and scale -----------------------------------------------------------------------


def test_many_simultaneous_requests_work_against_the_encrypted_pool(encrypted):
    for i in range(20):
        encrypted.make(f"note {i}")
    headers = encrypted.headers()

    def fetch(_):
        return encrypted.client.get("/api/items", headers=headers).status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(fetch, range(60)))

    assert codes == [200] * 60


def test_a_bigger_database_encrypts_and_comes_back_intact(env):
    for i in range(400):
        env.make(f"note {i}", "x" * 500)
    env.set_password()

    assert env.enable().status_code == 200
    assert len(env.titles()) == 400
    env.restart()
    env.unlock()
    assert len(env.titles()) == 400


def test_tags_embeddings_and_settings_survive_encryption(env):
    env.client.post("/api/items", json={"title": "tagged", "type": "NOTE", "tags": ["alpha"]}, headers=env.headers())
    env.set_password()
    env.client.put("/api/ai/settings", json={"enabled": True, "model": "m"}, headers=env.headers())

    env.enable()
    env.restart()
    env.unlock()

    assert env.get("/api/tags").json() == [{"name": "alpha", "count": 1}]
    assert env.get("/api/ai/status").json()["enabled"] is True


def test_exports_still_work_and_are_plain_by_design(encrypted):
    export = encrypted.get("/api/backup/export.json")

    assert export.status_code == 200 and MARKER in export.text  # an export is for the user to keep
