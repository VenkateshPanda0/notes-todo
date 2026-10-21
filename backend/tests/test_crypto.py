import hashlib
import sqlite3

import pytest

from backend.app.db import crypto

pytestmark = pytest.mark.skipif(not crypto.AVAILABLE, reason="sqlcipher3 is not installed")

SECRET = "TOP-SECRET-MARKER-9f3a"


def make_plain(path, rows=3, version=3):
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, title TEXT, body BLOB)")
    connection.execute("CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT)")
    connection.executemany("INSERT INTO items (title, body) VALUES (?, ?)", [(f"{SECRET}-{i}", b"\x00\x01" * 10) for i in range(rows)])
    connection.execute("INSERT INTO tags (name) VALUES ('t')")
    connection.execute(f"PRAGMA user_version = {version}")
    connection.commit()
    connection.close()
    return path


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# --- detecting encrypted files -------------------------------------------------------------------


def test_file_type_detection(tmp_path):
    plain = make_plain(tmp_path / "plain.db")
    encrypted = tmp_path / "enc.db"
    crypto.convert(plain, encrypted, None, "pw1234")
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    garbage = tmp_path / "garbage.db"
    garbage.write_bytes(b"this is definitely not sqlite " * 10)
    short = tmp_path / "short.db"
    short.write_bytes(b"XY")

    assert crypto.is_encrypted_file(plain) is False
    assert crypto.is_encrypted_file(encrypted) is True
    assert crypto.is_encrypted_file(tmp_path / "missing.db") is False
    assert crypto.is_encrypted_file(empty) is False  # a new, empty database is not "encrypted"
    assert crypto.is_encrypted_file(garbage) is True  # unknown content must go through the unlock path
    assert crypto.is_encrypted_file(short) is True


# --- opening with a key --------------------------------------------------------------------------


@pytest.mark.parametrize("password", ["simple", "has space", "quote'inside", 'double"quote', "unicode ✓ пароль 密码", "x" * 500, "semi;colon--comment", "pa'ss\"w0rd✓"])
def test_any_password_round_trips(tmp_path, password):
    plain = make_plain(tmp_path / "p.db")
    enc = tmp_path / "e.db"

    crypto.convert(plain, enc, None, password)
    connection = crypto.connect(enc, password)

    assert connection.execute("SELECT count(*) FROM items").fetchone()[0] == 3
    connection.close()


def test_a_wrong_password_is_rejected_with_a_clear_error(tmp_path):
    enc = tmp_path / "e.db"
    crypto.convert(make_plain(tmp_path / "p.db"), enc, None, "right-password")

    for wrong in ("wrong", "right-passwor", "RIGHT-PASSWORD", "right-password "):
        with pytest.raises(crypto.WrongPasswordError):
            crypto.connect(enc, wrong)


def test_opening_an_encrypted_file_without_a_password_is_rejected(tmp_path):
    enc = tmp_path / "e.db"
    crypto.convert(make_plain(tmp_path / "p.db"), enc, None, "pw1234")

    with pytest.raises(crypto.WrongPasswordError):
        crypto.connect(enc, None)


def test_the_encrypted_file_leaks_nothing_and_stock_sqlite_cannot_read_it(tmp_path):
    enc = tmp_path / "e.db"
    crypto.convert(make_plain(tmp_path / "p.db"), enc, None, "pw1234")
    data = enc.read_bytes()

    assert SECRET.encode() not in data
    assert b"SQLite format 3" not in data and b"CREATE TABLE" not in data and b"items" not in data
    with pytest.raises(sqlite3.DatabaseError):
        sqlite3.connect(enc).execute("SELECT * FROM items").fetchall()


def test_empty_passwords_are_refused_everywhere(tmp_path):
    plain = make_plain(tmp_path / "p.db")
    enc = tmp_path / "e.db"

    with pytest.raises(ValueError):
        crypto.convert(plain, enc, None, "")
    assert not enc.exists()  # nothing half-made, and certainly not a plain file posing as encrypted
    with pytest.raises(ValueError):
        crypto.connect(plain, "")
    crypto.convert(plain, enc, None, "pw1234")
    with pytest.raises(ValueError):
        crypto.rekey(enc, "pw1234", "")


# --- converting ----------------------------------------------------------------------------------


def test_plain_to_encrypted_to_plain_preserves_everything(tmp_path):
    plain = make_plain(tmp_path / "p.db", rows=7, version=5)
    enc, back = tmp_path / "e.db", tmp_path / "b.db"

    fp1 = crypto.convert(plain, enc, None, "pw1234")
    fp2 = crypto.convert(enc, back, "pw1234", None)

    assert fp1 == fp2 == {"tables": {"items": 7, "tags": 1}, "user_version": 5}
    connection = sqlite3.connect(back)  # readable by stock sqlite again
    assert connection.execute("SELECT title FROM items ORDER BY id LIMIT 1").fetchone() == (f"{SECRET}-0",)
    assert crypto.is_encrypted_file(back) is False
    connection.close()


def test_converting_never_modifies_the_source(tmp_path):
    plain = make_plain(tmp_path / "p.db")
    before = sha(plain)

    crypto.convert(plain, tmp_path / "e.db", None, "pw1234")

    assert sha(plain) == before


def test_a_wrong_source_password_leaves_no_destination_behind(tmp_path):
    enc = tmp_path / "e.db"
    crypto.convert(make_plain(tmp_path / "p.db"), enc, None, "pw1234")
    out = tmp_path / "out.db"

    with pytest.raises(crypto.WrongPasswordError):
        crypto.convert(enc, out, "nope", None)

    assert not out.exists()


def test_a_stale_destination_file_is_replaced_not_merged(tmp_path):
    plain = make_plain(tmp_path / "p.db", rows=2)
    out = tmp_path / "out.db"
    out.write_bytes(b"leftover from a crashed attempt")

    crypto.convert(plain, out, None, "pw1234")

    assert crypto.fingerprint_of(out, "pw1234")["tables"]["items"] == 2


def test_a_failed_verification_deletes_the_destination(tmp_path, monkeypatch):
    plain = make_plain(tmp_path / "p.db")
    out = tmp_path / "out.db"
    real = crypto.verify

    def lying_verify(path, password, expected):
        real(path, password, {**expected, "user_version": expected["user_version"] + 1})

    monkeypatch.setattr(crypto, "verify", lying_verify)

    with pytest.raises(crypto.VerificationError):
        crypto.convert(plain, out, None, "pw1234")

    assert not out.exists() and plain.exists()


def test_a_large_database_converts_with_all_rows(tmp_path):
    path = tmp_path / "big.db"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, title TEXT)")
    connection.executemany("INSERT INTO items (title) VALUES (?)", [(f"row {i} " + "x" * 200,) for i in range(8000)])
    connection.execute("PRAGMA user_version = 3")
    connection.commit()
    connection.close()

    fp = crypto.convert(path, tmp_path / "big-enc.db", None, "pw1234")

    assert fp["tables"]["items"] == 8000


def test_damage_to_an_encrypted_file_is_detected_by_verify(tmp_path):
    enc = tmp_path / "e.db"
    fp = crypto.convert(make_plain(tmp_path / "p.db", rows=50), enc, None, "pw1234")
    data = bytearray(enc.read_bytes())
    for i in range(4200, 4300):  # corrupt a later page, leaving page 1 (the one connect() reads) intact
        data[i] ^= 0xFF
    enc.write_bytes(bytes(data))

    with pytest.raises(crypto.VerificationError):
        crypto.verify(enc, "pw1234", fp)


# --- changing the password and deleting ----------------------------------------------------------


def test_rekey_changes_the_password_in_place(tmp_path):
    enc = tmp_path / "e.db"
    crypto.convert(make_plain(tmp_path / "p.db"), enc, None, "old-password")

    crypto.rekey(enc, "old-password", "new-password")

    with pytest.raises(crypto.WrongPasswordError):
        crypto.connect(enc, "old-password")
    assert crypto.fingerprint_of(enc, "new-password")["tables"]["items"] == 3
    assert crypto.is_encrypted_file(enc)


def test_rekey_with_the_wrong_old_password_changes_nothing(tmp_path):
    enc = tmp_path / "e.db"
    crypto.convert(make_plain(tmp_path / "p.db"), enc, None, "old-password")
    before = sha(enc)

    with pytest.raises(crypto.WrongPasswordError):
        crypto.rekey(enc, "WRONG", "new-password")

    assert sha(enc) == before


def test_secure_delete_removes_the_file_and_tolerates_missing_ones(tmp_path):
    victim = tmp_path / "v.db"
    victim.write_bytes(SECRET.encode() * 1000)

    crypto.secure_delete(victim)
    crypto.secure_delete(victim)  # already gone: not an error

    assert not victim.exists()


def test_secure_delete_overwrites_before_unlinking(tmp_path, monkeypatch):
    victim = tmp_path / "v.db"
    victim.write_bytes(SECRET.encode() * 1000)
    seen = {}
    real_unlink = type(victim).unlink

    def spy(self, *a, **k):
        seen["content_at_unlink"] = self.read_bytes()
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(type(victim), "unlink", spy)

    crypto.secure_delete(victim)

    assert seen["content_at_unlink"] == b"\x00" * (len(SECRET) * 1000)


def test_quote_escapes_quotes_and_drops_nul_bytes():
    assert crypto.quote("it's") == "'it''s'"
    assert crypto.quote("a\x00b") == "'ab'"
