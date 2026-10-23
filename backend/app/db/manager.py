"""Owns the database connection for the whole app.

Why this exists: with optional encryption the database file may not be openable when the server
starts (it needs the user's password first). So instead of a global engine created at import time,
one DatabaseManager decides at startup whether the file is plain (open it now) or encrypted (wait
for the password), and later handles unlocking, locking and switching between the two.
"""

import contextlib
import logging
import os
import shutil
import threading
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from . import crypto
from .crypto import VerificationError, WrongPasswordError  # noqa: F401  (re-exported for callers)

log = logging.getLogger("taskflow.db")

PLAIN_LEFTOVER = ".unencrypted"  # the original plain file, kept until the encrypted one is proven
ENCRYPTED_LEFTOVER = ".encrypted-old"  # the original encrypted file, kept during decryption
TEMP_SUFFIXES = (".encrypting", ".decrypting", ".rekey-backup")
EXCLUSIVE_TIMEOUT = 10.0  # seconds to wait for in-flight requests before a file switch gives up


class DatabaseBusyError(RuntimeError):
    """The database is being switched or re-keyed; try again in a moment."""


@dataclass
class EncryptionReport:
    removed_plain_backups: int


def sqlite_path(url: str) -> str | None:
    """The file path of a SQLite URL, or None for in-memory and non-SQLite databases."""
    parsed = make_url(url)
    if not parsed.drivername.startswith("sqlite") or parsed.database in (None, "", ":memory:"):
        return None
    return os.path.abspath(parsed.database)


class DatabaseManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._maintenance = False
        self._factory = sessionmaker(autocommit=False, autoflush=False)
        self.url: str | None = None
        self.path: str | None = None
        self.engine: Engine | None = None
        self.encrypted = False
        self._password: str | None = None

    # ---- state ---------------------------------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self.engine is not None

    @property
    def can_encrypt(self) -> bool:
        """Encryption needs SQLCipher in this build and a real database file."""
        return crypto.AVAILABLE and self.path is not None

    def key_for(self, engine: Engine) -> str | None:
        """The password of `engine` if it is the managed, encrypted engine (else None)."""
        return self._password if self.encrypted and engine is self.engine else None

    # ---- configuring and opening ---------------------------------------------------------------

    def configure(self, url: str) -> None:
        """Point the manager at a database. Plain files open immediately; encrypted ones wait."""
        with self._lock:
            self.close()
            self.url, self.path = url, sqlite_path(url)
            self.encrypted = False
            if self.path:
                self._recover_interrupted_switch()
            if self.path and crypto.is_encrypted_file(self.path):
                self.encrypted = True
                return  # needs unlock(password)
            self._install(self._plain_engine(url))

    def _plain_engine(self, url: str) -> Engine:
        return create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})

    def _encrypted_engine(self, path: str, password: str) -> Engine:
        crypto.connect(path, password).close()  # raises WrongPasswordError before an engine exists
        # Each new connection derives the key (deliberately slow), so keep connections pooled.
        return create_engine(
            f"sqlite:///{path}",
            creator=lambda: crypto.connect(path, password),
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
        )

    def _install(self, engine: Engine, password: str | None = None) -> None:
        self.engine = engine
        self._password = password
        self._factory.configure(bind=engine)

    def close(self) -> None:
        """Drop the connection and forget the password. The file is untouched."""
        with self._lock:
            if self.engine is not None:
                self.engine.dispose()
            self.engine = None
            self._password = None
            self._factory.configure(bind=None)

    def start(self) -> None:
        """Run schema setup and the daily backup for an open database (called at app startup)."""
        with self._lock:
            if self.engine is not None:
                self._after_open()

    def _after_open(self) -> None:
        from .session import init_database  # local import: session imports this module

        init_database(self.engine)
        from ..services.backup import run_auto_backup

        if os.getenv("TASKFLOW_DISABLE_AUTO_BACKUP") != "1":
            run_auto_backup(self.engine)
        self._purge_old_trash()
        if self.encrypted and self.path:  # the encrypted file just opened, so any plain leftover can go
            leftover = Path(self.path + PLAIN_LEFTOVER)
            if leftover.exists():
                crypto.secure_delete(leftover)

    def _purge_old_trash(self) -> None:
        """Permanently remove items that have sat in the Trash for more than 30 days."""
        from ..services.items import purge_expired_trash

        try:
            with Session(self.engine) as db:
                purge_expired_trash(db)
        except Exception:  # noqa: BLE001 - housekeeping must never stop the app from starting
            log.exception("Could not clean up the Trash")

    def unlock(self, password: str) -> None:
        """Open an encrypted database. Raises WrongPasswordError for a bad password."""
        with self._lock:
            if self.engine is not None:
                return
            crypto.require_available()
            assert self.path is not None
            engine = self._encrypted_engine(self.path, password)
            self._install(engine, password)
            try:
                self._after_open()
            except Exception:
                self.close()
                raise

    # ---- sessions ------------------------------------------------------------------------------

    def session(self) -> Session | None:
        """A new session, or None while the database is locked. Raises DatabaseBusyError mid-switch."""
        if self._maintenance:
            raise DatabaseBusyError("TaskFlow is busy updating your data. Try again in a moment.")
        if self.engine is None:
            return None
        return self._factory()

    @contextlib.contextmanager
    def _exclusive(self, timeout: float | None = None) -> Iterator[None]:
        """Block new sessions and wait for in-flight ones to finish, so the file can be swapped."""
        with self._lock:
            if self._maintenance:
                raise DatabaseBusyError("TaskFlow is busy updating your data. Try again in a moment.")
            self._maintenance = True
        try:
            deadline = time.monotonic() + (EXCLUSIVE_TIMEOUT if timeout is None else timeout)
            while self.engine is not None and getattr(self.engine.pool, "checkedout", lambda: 0)() > 0:
                if time.monotonic() > deadline:
                    raise DatabaseBusyError("The database is in use. Try again in a moment.")
                time.sleep(0.05)
            yield
        finally:
            self._maintenance = False

    # ---- crash recovery ------------------------------------------------------------------------

    def _recover_interrupted_switch(self) -> None:
        """Undo a half-finished encrypt/decrypt left by a crash or power loss.

        The original file is only ever renamed aside (never deleted) until the replacement has been
        verified, so if the main file is missing the renamed original is put back.
        """
        assert self.path
        main = Path(self.path)
        for leftover in (Path(self.path + PLAIN_LEFTOVER), Path(self.path + ENCRYPTED_LEFTOVER)):
            if not main.exists() and leftover.exists():
                os.replace(leftover, main)
                log.warning("Restored %s after an interrupted switch", main.name)
        for suffix in TEMP_SUFFIXES:  # unfinished work files are always safe to discard
            Path(self.path + suffix).unlink(missing_ok=True)

    # ---- switching on/off encryption, changing the password -----------------------------------

    def encrypt_database(self, password: str) -> EncryptionReport:
        """Encrypt the plain database in place, with verification and a way back at every step."""
        crypto.require_available()
        with self._exclusive():
            if self.encrypted or self.engine is None or not self.path:
                raise RuntimeError("The database is not in a state that can be encrypted.")
            source = Path(self.path)
            building, aside = Path(self.path + ".encrypting"), Path(self.path + PLAIN_LEFTOVER)
            self.engine.dispose()
            try:
                expected = crypto.convert(source, building, None, password)  # verified before returning
            except Exception:
                self._reopen_plain()
                raise
            os.replace(source, aside)
            try:
                os.replace(building, source)
            except OSError:
                os.replace(aside, source)
                self._reopen_plain()
                raise
            try:
                engine = self._encrypted_engine(self.path, password)
                crypto.verify(source, password, expected)
            except Exception:
                # The encrypted file is not usable: put the plain original back exactly as it was.
                with contextlib.suppress(Exception):
                    engine.dispose()
                failed = Path(self.path + ".failed-encrypted")
                os.replace(source, failed)
                os.replace(aside, source)
                failed.unlink(missing_ok=True)  # an unusable encrypted file has no value to anyone
                self._reopen_plain()
                raise
            self.encrypted = True
            self._install(engine, password)
            crypto.secure_delete(aside)
            Path(self.path + ".failed-encrypted").unlink(missing_ok=True)
            removed = self._wipe_plain_backups()
        from ..services.backup import run_auto_backup

        run_auto_backup(self.engine, force=True)  # a fresh, encrypted snapshot
        return EncryptionReport(removed_plain_backups=removed)

    def decrypt_database(self, password: str) -> None:
        """Turn encryption off again (the user's choice), with the same verify-then-swap safety."""
        crypto.require_available()
        with self._exclusive():
            if not self.encrypted or self.engine is None or not self.path:
                raise RuntimeError("The database is not encrypted.")
            source = Path(self.path)
            building, aside = Path(self.path + ".decrypting"), Path(self.path + ENCRYPTED_LEFTOVER)
            self.engine.dispose()
            try:
                expected = crypto.convert(source, building, password, None)
            except Exception:
                self._reopen_encrypted(password)
                raise
            os.replace(source, aside)
            try:
                os.replace(building, source)
                crypto.verify(source, None, expected)
            except Exception:
                os.replace(source, Path(self.path + ".failed-decrypted"))
                os.replace(aside, source)
                Path(self.path + ".failed-decrypted").unlink(missing_ok=True)
                self._reopen_encrypted(password)
                raise
            self.encrypted = False
            self._install(self._plain_engine(self.url))  # type: ignore[arg-type]
            aside.unlink(missing_ok=True)

    def change_password(self, old_password: str, new_password: str) -> None:
        """Re-key an encrypted database (and best-effort its backups) to a new password."""
        crypto.require_available()
        with self._exclusive():
            if not self.encrypted or self.engine is None or not self.path:
                raise RuntimeError("The database is not encrypted.")
            safety = Path(self.path + ".rekey-backup")
            self.engine.dispose()
            shutil.copy2(self.path, safety)
            try:
                crypto.rekey(self.path, old_password, new_password)
            except Exception:
                safety.unlink(missing_ok=True)
                self._reopen_encrypted(old_password)
                raise
            self._install(self._encrypted_engine(self.path, new_password), new_password)
            safety.unlink(missing_ok=True)
            self._rekey_backups(old_password, new_password)

    # ---- helpers -------------------------------------------------------------------------------

    def _reopen_plain(self) -> None:
        self._install(self._plain_engine(self.url))  # type: ignore[arg-type]

    def _reopen_encrypted(self, password: str) -> None:
        self._install(self._encrypted_engine(self.path, password), password)  # type: ignore[arg-type]

    def _backup_files(self) -> list[Path]:
        from ..services.backup import backup_directory

        directory = backup_directory(self.engine) if self.engine is not None else None
        if directory is None or not directory.is_dir():
            return []
        from ..services.backup import is_backup_name

        return [p for p in directory.iterdir() if is_backup_name(p.name)]

    def _wipe_plain_backups(self) -> int:
        """Securely delete every backup that is NOT encrypted (made before encryption was on)."""
        removed = 0
        for path in self._backup_files():
            if not crypto.is_encrypted_file(path):
                crypto.secure_delete(path)
                removed += 1
        return removed

    def _rekey_backups(self, old_password: str, new_password: str) -> None:
        for path in self._backup_files():
            try:
                crypto.rekey(path, old_password, new_password)
            except Exception:  # noqa: BLE001 - best effort: an unreadable backup is left as it is
                log.warning("Could not re-key backup %s", path.name)


manager = DatabaseManager()
