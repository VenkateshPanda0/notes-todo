"""SQLCipher helpers: opening, converting and verifying encrypted SQLite files.

The optional `sqlcipher3` package provides the encryption. Everything here degrades cleanly when it
is missing: `AVAILABLE` is False and plain databases keep working exactly as before.

Safety rules the rest of the app relies on:
  * Converting never touches the source file. It writes a new file, which is then verified
    (integrity check, same tables, same row counts, same schema version) before anyone swaps it in.
  * A wrong password is always reported as WrongPasswordError, never as silent corruption.
"""

import os
import sqlite3
from pathlib import Path

try:  # optional native dependency
    from sqlcipher3 import dbapi2 as sqlcipher
except ImportError:  # pragma: no cover - exercised only on builds without sqlcipher3
    sqlcipher = None

AVAILABLE = sqlcipher is not None
SQLITE_MAGIC = b"SQLite format 3\x00"


class EncryptionUnavailableError(RuntimeError):
    """This build has no SQLCipher support."""


class WrongPasswordError(Exception):
    """The password does not open the database."""


class VerificationError(Exception):
    """A converted database did not match its source; the conversion was abandoned."""


def require_available() -> None:
    if not AVAILABLE:
        raise EncryptionUnavailableError("This build of TaskFlow does not include database encryption.")


def is_encrypted_file(path: str | os.PathLike) -> bool:
    """True if the file exists and does not start with the plain SQLite header.

    A SQLCipher file looks like random bytes from the first byte, so anything that is non-empty and
    lacks the plain header is treated as encrypted (or corrupt: either way it needs the unlock path).
    """
    try:
        with open(path, "rb") as handle:
            header = handle.read(len(SQLITE_MAGIC))
    except FileNotFoundError:
        return False
    if not header:
        return False  # an empty file is a brand-new database, not an encrypted one
    return header != SQLITE_MAGIC[: len(header)]


def quote(value: str) -> str:
    """A SQL string literal for `value` (PRAGMA statements cannot take bound parameters)."""
    return "'" + value.replace("'", "''").replace("\x00", "") + "'"


def connect(path: str | os.PathLike, password: str | None, *, check_same_thread: bool = False):
    """Open a database with SQLCipher. `password=None` opens a plain (unencrypted) file.

    Raises WrongPasswordError if the key is wrong or the file is not a database at all.
    """
    require_available()
    if password is not None and not password:
        # An empty key means "no encryption" to SQLCipher, which would silently defeat the point.
        raise ValueError("The password must not be empty.")
    connection = sqlcipher.connect(str(path), check_same_thread=check_same_thread)
    try:
        if password is not None:
            connection.execute(f"PRAGMA key = {quote(password)}")
        # The key is only checked lazily; reading the schema forces it.
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlcipher.DatabaseError as exc:
        connection.close()
        raise WrongPasswordError("Incorrect password.") from exc
    return connection


def _tables(connection) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def fingerprint(connection) -> dict:
    """What a conversion must preserve: tables, row counts and the schema version."""
    return {
        "tables": {t: connection.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in _tables(connection)},
        "user_version": connection.execute("PRAGMA user_version").fetchone()[0],
    }


def fingerprint_of(path: str | os.PathLike, password: str | None) -> dict:
    connection = connect(path, password)
    try:
        return fingerprint(connection)
    finally:
        connection.close()


def convert(source: str | os.PathLike, destination: str | os.PathLike, source_password: str | None,
            destination_password: str | None) -> dict:
    """Copy `source` into a NEW file at `destination` with a different password (or none).

    The destination is verified against the source before this returns; on any problem the
    destination is deleted and the error raised. The source is only ever read.
    """
    require_available()
    if destination_password is not None and not destination_password:
        raise ValueError("The password must not be empty.")
    destination = Path(destination)
    if destination.exists():
        destination.unlink()
    source_connection = connect(source, source_password)
    try:
        expected = fingerprint(source_connection)
        key = quote(destination_password) if destination_password is not None else "''"
        source_connection.execute(f"ATTACH DATABASE {quote(str(destination))} AS converted KEY {key}")
        source_connection.execute("SELECT sqlcipher_export('converted')")
        source_connection.execute(f"PRAGMA converted.user_version = {int(expected['user_version'])}")
        source_connection.commit()
        source_connection.execute("DETACH DATABASE converted")
    except Exception:
        source_connection.close()
        destination.unlink(missing_ok=True)
        raise
    source_connection.close()

    try:
        verify(destination, destination_password, expected)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return expected


def verify(path: str | os.PathLike, password: str | None, expected: dict) -> None:
    """Raise VerificationError unless the database is sound and matches `expected`."""
    connection = connect(path, password)
    try:
        try:
            result = connection.execute("PRAGMA integrity_check").fetchone()[0]
            actual = fingerprint(connection)
        except sqlcipher.DatabaseError as exc:  # damaged pages surface as errors, not as a result row
            raise VerificationError(f"The database is damaged: {exc}") from exc
        if result != "ok":
            raise VerificationError(f"Integrity check failed: {result}")
    finally:
        connection.close()
    if actual != expected:
        raise VerificationError(f"The converted database does not match the original ({actual} vs {expected}).")
    # An encrypted file must really be unreadable without the key, and a plain one readable without.
    encrypted = is_encrypted_file(path)
    if (password is not None) != encrypted:
        raise VerificationError("The converted file is not in the expected (encrypted/plain) format.")


def rekey(path: str | os.PathLike, old_password: str, new_password: str) -> None:
    """Change an encrypted database's password in place (needs exclusive access to the file)."""
    if not new_password:
        raise ValueError("The password must not be empty.")
    connection = connect(path, old_password)
    try:
        connection.execute(f"PRAGMA rekey = {quote(new_password)}")
    finally:
        connection.close()
    connect(path, new_password).close()  # prove the new password opens it


def secure_delete(path: str | os.PathLike) -> None:
    """Overwrite a file with zeros, then delete it. Best effort: SSD wear levelling and file system
    journals can keep old blocks, so this lowers the chance of recovery rather than eliminating it."""
    path = Path(path)
    try:
        size = path.stat().st_size
        with open(path, "r+b") as handle:
            remaining = size
            block = b"\x00" * (1024 * 1024)
            while remaining > 0:
                handle.write(block[: min(len(block), remaining)])
                remaining -= len(block)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError:
        pass
    path.unlink(missing_ok=True)


def sqlite_plain_connect(path: str | os.PathLike):
    """A plain stdlib connection, used only to prove a file is NOT readable as plain SQLite."""
    return sqlite3.connect(str(path))
