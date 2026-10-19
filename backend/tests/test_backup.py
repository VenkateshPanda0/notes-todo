import io
import json
import sqlite3
import zipfile
from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from backend.app.db.session import init_database
from backend.app.services import backup as backup_service


def make(client, title, content="", type="NOTE", **extra):
    response = client.post("/api/items", json={"title": title, "type": type, "content": content, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def items(client):
    return client.get("/api/items").json()


def import_(client, body, mode="merge", content_type="application/json"):
    if isinstance(body, (dict, list)):
        body = json.dumps(body)
    return client.post(f"/api/backup/import?mode={mode}", content=body, headers={"Content-Type": content_type})


def seed(client):
    make(client, "Trip plan", "Visit [[Kyoto]]\n\n- sushi", tags=["travel", "ideas"])
    make(client, "Pay rent", type="TODO", priority="HIGH", due_date="2026-11-01", tags=["home"])
    done = make(client, "File taxes", "all done", type="TODO", priority="LOW")
    client.post(f"/api/items/{done['id']}/complete")


def zip_of(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


# --- JSON export ---------------------------------------------------------------------------------


def test_json_export_is_a_complete_versioned_file(client):
    seed(client)

    response = client.get("/api/backup/export.json")
    data = response.json()

    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"] and ".json" in response.headers["content-disposition"]
    assert data["format"] == "taskflow-export" and data["version"] == 1 and data["exported_at"]
    assert [i["title"] for i in data["items"]] == ["Trip plan", "Pay rent", "File taxes"]
    rent = data["items"][1]
    assert (rent["type"], rent["priority"], rent["due_date"], rent["tags"]) == ("TODO", "HIGH", "2026-11-01", ["home"])
    assert data["items"][2]["completed"] is True
    assert data["items"][0]["created_at"]


def test_json_round_trip_restores_everything_after_a_wipe(client):
    seed(client)
    export = client.get("/api/backup/export.json").content
    before = [{k: v for k, v in i.items() if k not in ("id", "updated_at")} for i in items(client)]
    for item in items(client):
        client.delete(f"/api/items/{item['id']}")
    assert items(client) == []

    result = import_(client, export).json()

    after = [{k: v for k, v in i.items() if k not in ("id", "updated_at")} for i in items(client)]
    assert result == {"mode": "merge", "imported": 3, "skipped": 0}
    assert sorted(after, key=lambda i: i["title"]) == sorted(before, key=lambda i: i["title"])


def test_import_preserves_original_timestamps(client):
    payload = {
        "format": "taskflow-export", "version": 1,
        "items": [{"title": "Old", "type": "NOTE", "created_at": "2020-01-02T03:04:05+00:00"}],
    }

    import_(client, payload)

    assert items(client)[0]["created_at"].startswith("2020-01-02T03:04:05")


# --- merge / replace -----------------------------------------------------------------------------


def test_merge_is_idempotent_and_skips_items_already_present(client):
    seed(client)
    export = client.get("/api/backup/export.json").content

    first = import_(client, export).json()
    second = import_(client, export, mode="merge").json()

    assert first == {"mode": "merge", "imported": 0, "skipped": 3}
    assert second["imported"] == 0
    assert len(items(client)) == 3


def test_merge_adds_only_new_items_and_keeps_existing_ones(client):
    make(client, "Existing", "keep me")
    payload = {"format": "taskflow-export", "version": 1, "items": [
        {"title": "Existing", "type": "NOTE", "content": "keep me"},
        {"title": "Brand new", "type": "NOTE"},
    ]}

    result = import_(client, payload).json()

    assert (result["imported"], result["skipped"]) == (1, 1)
    assert sorted(i["title"] for i in items(client)) == ["Brand new", "Existing"]


def test_same_title_but_different_type_or_content_is_not_a_duplicate(client):
    make(client, "Same", "a", type="NOTE")
    payload = {"format": "taskflow-export", "version": 1, "items": [
        {"title": "Same", "type": "TODO", "content": "a"},
        {"title": "Same", "type": "NOTE", "content": "b"},
    ]}

    assert import_(client, payload).json()["imported"] == 2


def test_replace_swaps_everything_and_cleans_up_tags(client):
    make(client, "Old note", tags=["oldtag"])
    payload = {"format": "taskflow-export", "version": 1, "items": [{"title": "Fresh", "type": "NOTE", "tags": ["newtag"]}]}

    result = import_(client, payload, mode="replace").json()

    assert result == {"mode": "replace", "imported": 1, "skipped": 0}
    assert [i["title"] for i in items(client)] == ["Fresh"]
    assert client.get("/api/tags").json() == [{"name": "newtag", "count": 1}]


def test_a_failed_replace_leaves_existing_data_untouched(client, monkeypatch):
    make(client, "Precious")
    payload = {"format": "taskflow-export", "version": 1, "items": [
        {"title": "A", "type": "NOTE"}, {"title": "B", "type": "NOTE"}]}
    calls = {"n": 0}
    original = backup_service._resolve_tags

    def flaky(db, names):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("disk exploded")
        return original(db, names)

    monkeypatch.setattr(backup_service, "_resolve_tags", flaky)

    with pytest.raises(RuntimeError):
        import_(client, payload, mode="replace")

    monkeypatch.undo()
    assert [i["title"] for i in items(client)] == ["Precious"]


def test_invalid_tags_in_an_import_are_skipped_not_fatal(client):
    payload = {"format": "taskflow-export", "version": 1, "items": [
        {"title": "T", "type": "NOTE", "tags": ["good", "bad tag!", "#Also-Good", "good"]}]}

    import_(client, payload)

    assert items(client)[0]["tags"] == ["also-good", "good"]


def test_unknown_mode_is_rejected(client):
    assert import_(client, {"format": "taskflow-export", "version": 1, "items": []}, mode="nuke").status_code == 422


# --- bad files -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"not json at all", "not valid JSON"),
        (b"[1, 2, 3]", "not a TaskFlow export"),
        (b'{"format": "something-else", "version": 1, "items": []}', "not a TaskFlow export"),
        (b'{"format": "taskflow-export", "version": 99, "items": []}', "newer TaskFlow"),
        (b'{"format": "taskflow-export", "version": 1, "items": [{"title": "", "type": "NOTE"}]}', "damaged at 'items.0.title'"),
        (b'{"format": "taskflow-export", "version": 1, "items": [{"title": "x", "type": "BOGUS"}]}', "damaged"),
        (b"PK\x03\x04 this is not really a zip", "not a valid zip"),
    ],
)
def test_bad_files_get_a_clear_422_and_change_nothing(client, body, message):
    make(client, "Safe")

    response = import_(client, body)

    assert response.status_code == 422
    assert message in response.json()["detail"]
    assert [i["title"] for i in items(client)] == ["Safe"]


def test_oversized_uploads_are_refused_up_front(client, monkeypatch):
    monkeypatch.setattr(backup_service, "MAX_UPLOAD_BYTES", 10)

    assert import_(client, b"x" * 50).status_code == 413


def test_zip_without_markdown_files_is_rejected(client):
    response = import_(client, zip_of({"readme.txt": "hi"}), content_type="application/zip")

    assert response.status_code == 422 and "No Markdown" in response.json()["detail"]


# --- Markdown export / import --------------------------------------------------------------------


def test_markdown_export_lays_out_one_file_per_item_with_front_matter(client):
    seed(client)

    response = client.get("/api/backup/export.zip")
    archive = zipfile.ZipFile(io.BytesIO(response.content))

    assert response.headers["content-type"] == "application/zip"
    assert sorted(archive.namelist()) == ["Notes/Trip plan.md", "Todos/File taxes.md", "Todos/Pay rent.md"]
    note = archive.read("Notes/Trip plan.md").decode()
    assert note.startswith('---\ntitle: "Trip plan"\ntype: note\ntags: [ideas, travel]\n')
    assert "Visit [[Kyoto]]" in note and note.rstrip().endswith("- sushi")
    rent = archive.read("Todos/Pay rent.md").decode()
    assert "completed: false" in rent and "priority: high" in rent and "due: 2026-11-01" in rent


def test_markdown_export_sanitizes_and_deduplicates_filenames(client):
    make(client, 'What/is: this?*')
    make(client, "Same")
    make(client, "Same")
    make(client, "...")
    make(client, "日本語のノート")

    names = sorted(zipfile.ZipFile(io.BytesIO(client.get("/api/backup/export.zip").content)).namelist())

    assert names == [
        "Notes/Same (2).md",
        "Notes/Same.md",
        "Notes/What-is- this.md",
        "Notes/untitled.md",
        "Notes/日本語のノート.md",
    ]


def test_markdown_round_trip_keeps_type_tags_priority_due_and_completion(client):
    seed(client)
    export = client.get("/api/backup/export.zip").content
    before = {i["title"]: i for i in items(client)}
    for item in items(client):
        client.delete(f"/api/items/{item['id']}")

    result = import_(client, export, content_type="application/zip").json()
    after = {i["title"]: i for i in items(client)}

    assert result["imported"] == 3
    for title, original in before.items():
        for field in ("type", "content", "completed", "priority", "due_date", "tags"):
            assert after[title][field] == original[field], (title, field)


def test_markdown_import_understands_common_obsidian_front_matter(client):
    files = {
        "Inbox/Block list.md": '---\ntags:\n  - alpha\n  - "Beta"\n---\nbody one',
        "Inbox/Flow list.md": "---\ntags: [x, y]\n---\nbody two",
        "Inbox/String tags.md": "---\ntags: one two, three\n---\nbody three",
        "Plain.md": "no front matter, just text",
        "Todos/Chore.md": "---\ncompleted: true\npriority: low\ndue: 2026-12-24\n---\nwash car",
        "CRLF.md": "---\r\ntitle: Windows file\r\n---\r\nline",
        "BOM.md": "﻿---\ntitle: With BOM\n---\nbody",
        "Quoted.md": '---\ntitle: "Quoted: title"\ntype: note\ndue: 2026-01-01\n---\nnotes ignore due dates',
        "Bad due.md": "---\ntype: todo\ndue: not-a-date\n---\nx",
        "notes.txt": "ignored",
    }

    result = import_(client, zip_of(files), content_type="application/zip").json()
    got = {i["title"]: i for i in items(client)}

    assert result["imported"] == 9
    assert got["Block list"]["tags"] == ["alpha", "beta"] and got["Block list"]["content"] == "body one"
    assert got["Flow list"]["tags"] == ["x", "y"]
    assert got["String tags"]["tags"] == ["one", "three", "two"]
    assert got["Plain"]["type"] == "NOTE" and got["Plain"]["content"] == "no front matter, just text"
    chore = got["Chore"]
    assert (chore["type"], chore["completed"], chore["priority"], chore["due_date"]) == ("TODO", True, "LOW", "2026-12-24")
    assert "Windows file" in got and "With BOM" in got
    assert got["Quoted: title"]["due_date"] is None
    assert got["Bad due"]["type"] == "TODO" and got["Bad due"]["due_date"] is None


def test_markdown_import_merge_is_idempotent(client):
    zipped = zip_of({"A.md": "---\ntitle: A\n---\nbody"})

    first = import_(client, zipped, content_type="application/zip").json()
    second = import_(client, zipped, content_type="application/zip").json()

    assert (first["imported"], second["imported"], second["skipped"]) == (1, 0, 1)


# --- database copy -------------------------------------------------------------------------------


def test_database_download_is_a_valid_sqlite_file_with_the_data(client, tmp_path):
    seed(client)

    response = client.get("/api/backup/database")
    copy = tmp_path / "copy.db"
    copy.write_bytes(response.content)

    assert response.status_code == 200
    assert ".db" in response.headers["content-disposition"]
    connection = sqlite3.connect(copy)
    try:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert [r[0] for r in connection.execute("SELECT title FROM items ORDER BY id")] == ["Trip plan", "Pay rent", "File taxes"]
    finally:
        connection.close()


# --- automatic backups ---------------------------------------------------------------------------


@pytest.fixture()
def file_engine(tmp_path):
    (tmp_path / "data").mkdir()
    engine = create_engine(f"sqlite:///{tmp_path / 'data' / 'flow.db'}")
    init_database(engine)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO items (title, content, type, completed, priority, created_at, updated_at) "
            "VALUES ('Saved', '', 'NOTE', 0, 'LOW', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"))
    yield engine
    engine.dispose()


def test_auto_backup_creates_a_snapshot_beside_the_database(file_engine, tmp_path):
    path = backup_service.run_auto_backup(file_engine, today=date(2026, 3, 5))

    assert path == (tmp_path / "data" / "backups" / "flow-2026-03-05.db").resolve()
    connection = sqlite3.connect(path)
    try:
        assert connection.execute("SELECT title FROM items").fetchone() == ("Saved",)
    finally:
        connection.close()
    assert [b.name for b in backup_service.list_auto_backups(file_engine)] == ["flow-2026-03-05.db"]


def test_auto_backup_runs_once_per_day_unless_forced(file_engine):
    first = backup_service.run_auto_backup(file_engine, today=date(2026, 3, 5))
    first.write_bytes(b"marker")

    backup_service.run_auto_backup(file_engine, today=date(2026, 3, 5))
    assert first.read_bytes() == b"marker"  # untouched

    backup_service.run_auto_backup(file_engine, today=date(2026, 3, 5), force=True)
    assert first.read_bytes() != b"marker"


def test_auto_backup_keeps_only_the_newest_and_ignores_other_files(file_engine):
    directory = backup_service.backup_directory(file_engine)
    directory.mkdir(parents=True)
    (directory / "notes.txt").write_text("not a backup")
    for day in range(1, 11):
        backup_service.run_auto_backup(file_engine, today=date(2026, 3, 1) + timedelta(days=day - 1), keep=3)

    names = [b.name for b in backup_service.list_auto_backups(file_engine)]

    assert names == ["flow-2026-03-10.db", "flow-2026-03-09.db", "flow-2026-03-08.db"]
    assert (directory / "notes.txt").exists()


def test_auto_backup_never_raises(file_engine, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(backup_service, "snapshot_database", boom)

    assert backup_service.run_auto_backup(file_engine, today=date(2026, 3, 5)) is None


def test_before_import_snapshots_are_separate_and_survive_daily_pruning(file_engine):
    directory = backup_service.backup_directory(file_engine)
    safety = backup_service.snapshot_before_import(file_engine, now=datetime(2026, 3, 5, 12, 0, 0))
    for day in range(1, 6):
        backup_service.run_auto_backup(file_engine, today=date(2026, 4, day), keep=2)

    assert safety.name == "before-import-20260305-120000.db" and safety.exists()
    names = [b.name for b in backup_service.list_auto_backups(file_engine)]
    assert "before-import-20260305-120000.db" in names
    assert sum(n.startswith("flow-") for n in names) == 2
    assert directory.exists()


def test_only_the_newest_before_import_snapshots_are_kept(file_engine):
    for minute in range(5):
        backup_service.snapshot_before_import(file_engine, now=datetime(2026, 3, 5, 12, minute, 0))

    names = sorted(b.name for b in backup_service.list_auto_backups(file_engine))

    assert names == [f"before-import-20260305-12{m:02d}00.db" for m in (2, 3, 4)]


def test_snapshot_failure_aborts_with_a_clear_error(file_engine, monkeypatch):
    monkeypatch.setattr(backup_service, "snapshot_database", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))

    with pytest.raises(backup_service.BackupFileError, match="nothing was changed"):
        backup_service.snapshot_before_import(file_engine)


def test_replace_import_takes_a_safety_snapshot_first(tmp_path):
    """End to end against a real file database: the snapshot holds the pre-import data."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from backend.app.api.deps import get_db
    from backend.app.main import app

    (tmp_path / "data").mkdir()
    engine = create_engine(
        f"sqlite:///{tmp_path / 'data' / 'flow.db'}", connect_args={"check_same_thread": False}
    )
    init_database(engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        with TestClient(app) as c:
            make(c, "Before the replace")
            payload = {"format": "taskflow-export", "version": 1, "items": [{"title": "After", "type": "NOTE"}]}
            assert import_(c, payload, mode="replace").status_code == 200
            snapshots = list((tmp_path / "data" / "backups").glob("before-import-*.db"))
            assert len(snapshots) == 1
            connection = sqlite3.connect(snapshots[0])
            try:
                assert [r[0] for r in connection.execute("SELECT title FROM items")] == ["Before the replace"]
            finally:
                connection.close()
            assert [i["title"] for i in items(c)] == ["After"]

            # merge mode must not create one, and a bad replace file must not either
            import_(c, payload, mode="merge")
            import_(c, b"garbage", mode="replace")
            assert len(list((tmp_path / "data" / "backups").glob("before-import-*.db"))) == 1
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_in_memory_databases_have_no_auto_backups(client):
    body = client.get("/api/backup/auto").json()

    assert body == {"enabled": False, "directory": None, "backups": []}
    assert client.post("/api/backup/auto/run").status_code == 400


# --- access control ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/backup/export.json"), ("get", "/api/backup/export.zip"), ("get", "/api/backup/database"),
     ("post", "/api/backup/import"), ("get", "/api/backup/auto"), ("post", "/api/backup/auto/run")],
)
def test_every_backup_route_requires_the_session_when_locked(client, method, path):
    client.post("/api/auth/setup", json={"password": "secret1"})

    assert getattr(client, method)(path).status_code == 401
