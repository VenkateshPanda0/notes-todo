import hashlib
import hmac
import os

from sqlalchemy.orm import Session

from ..models.app_settings import AppSettings

_ITERATIONS = 200_000


class IncorrectPasswordError(Exception):
    """Raised when a supplied password does not match the stored hash."""


class PasswordAlreadySetError(Exception):
    """Raised when trying to set a password while one is already configured."""


class NoPasswordSetError(Exception):
    """Raised when an unlock/change is attempted but no password is configured."""


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, digest_hex = stored_hash.split("$")
    salt = bytes.fromhex(salt_hex)
    candidate = _hash_password(password, salt)
    return hmac.compare_digest(candidate, stored_hash)


def get_settings_row(db: Session) -> AppSettings | None:
    return db.get(AppSettings, 1)


def is_locked(db: Session) -> bool:
    """True if a password has been configured for the app."""
    return get_settings_row(db) is not None


def set_password(db: Session, password: str) -> None:
    """Configure the app lock password for the first time."""
    if is_locked(db):
        raise PasswordAlreadySetError()
    settings = AppSettings(id=1, password_hash=_hash_password(password))
    db.add(settings)
    db.commit()


def unlock(db: Session, password: str) -> None:
    """Verify a password attempt against the configured lock."""
    settings = get_settings_row(db)
    if settings is None:
        raise NoPasswordSetError()
    if not _verify_password(password, settings.password_hash):
        raise IncorrectPasswordError()


def change_password(db: Session, current_password: str, new_password: str) -> None:
    """Change the app lock password after verifying the current one."""
    settings = get_settings_row(db)
    if settings is None:
        raise NoPasswordSetError()
    if not _verify_password(current_password, settings.password_hash):
        raise IncorrectPasswordError()
    settings.password_hash = _hash_password(new_password)
    db.commit()
