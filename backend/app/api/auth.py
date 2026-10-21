import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db import crypto
from ..db.manager import DatabaseBusyError, manager
from ..schemas.auth import (
    ChangePasswordRequest,
    EncryptionRequest,
    EncryptionResult,
    LockStatus,
    SessionToken,
    SetPasswordRequest,
    UnlockRequest,
)
from ..services import auth as auth_service
from ..services import session as session_service
from ..services.auth import (
    IncorrectPasswordError,
    NoPasswordSetError,
    PasswordAlreadySetError,
)
from ..services.session import TooManyAttemptsError
from .deps import extract_bearer_token, get_db, require_unlocked

log = logging.getLogger("taskflow.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _too_many_attempts(exc: TooManyAttemptsError) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"Too many failed attempts. Try again in {exc.retry_after} seconds.",
        headers={"Retry-After": str(exc.retry_after)},
    )


def _busy(exc: DatabaseBusyError) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _check_attempts() -> None:
    try:
        session_service.check_attempts_allowed()
    except TooManyAttemptsError as exc:
        raise _too_many_attempts(exc) from exc


def _verify_or_401(db: Session, password: str, message: str = "Incorrect password") -> None:
    """Check the App Lock password, counting a failure toward the lockout."""
    try:
        auth_service.verify_current(db, password)
    except NoPasswordSetError as exc:
        raise HTTPException(status_code=409, detail="No password configured") from exc
    except IncorrectPasswordError as exc:
        session_service.record_failed_attempt()
        raise HTTPException(status_code=401, detail=message) from exc
    session_service.record_successful_attempt()


@router.get("/status", response_model=LockStatus)
def get_lock_status(db: Session | None = Depends(get_db)) -> LockStatus:
    """Whether the app is locked, and whether its database file is encrypted."""
    if db is None:  # an encrypted database that has not been opened yet
        return LockStatus(is_locked=True, encrypted=True, encryption_available=crypto.AVAILABLE)
    return LockStatus(
        is_locked=auth_service.is_locked(db),
        encrypted=manager.encrypted,
        encryption_available=manager.can_encrypt,
    )


@router.post("/setup", response_model=SessionToken)
def setup_password(payload: SetPasswordRequest, db: Session | None = Depends(get_db)) -> SessionToken:
    """Configure the app lock password for the first time and start a session."""
    if db is None:
        raise HTTPException(status_code=409, detail="Password already set")
    try:
        auth_service.set_password(db, payload.password)
    except PasswordAlreadySetError as exc:
        raise HTTPException(status_code=409, detail="Password already set") from exc
    return SessionToken(token=session_service.issue_token())


@router.post("/unlock", response_model=SessionToken)
def unlock(payload: UnlockRequest, db: Session | None = Depends(get_db)) -> SessionToken:
    """Verify the app lock password and start a session.

    For an encrypted database the password is the key: unlocking is what opens the file.
    """
    _check_attempts()

    if db is None:
        try:
            manager.unlock(payload.password)
        except crypto.WrongPasswordError as exc:
            session_service.record_failed_attempt()
            raise HTTPException(status_code=401, detail="Incorrect password") from exc
        except crypto.EncryptionUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except DatabaseBusyError as exc:
            raise _busy(exc) from exc
        except RuntimeError as exc:  # e.g. the database is from a newer TaskFlow
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        session_service.record_successful_attempt()
        return SessionToken(token=session_service.issue_token())

    try:
        auth_service.unlock(db, payload.password)
    except NoPasswordSetError as exc:
        raise HTTPException(status_code=409, detail="No password configured") from exc
    except IncorrectPasswordError as exc:
        session_service.record_failed_attempt()
        raise HTTPException(status_code=401, detail="Incorrect password") from exc

    session_service.record_successful_attempt()
    return SessionToken(token=session_service.issue_token())


@router.post("/lock", status_code=204)
def lock(authorization: str | None = Header(default=None)) -> None:
    """End the current session so the app must be unlocked again.

    With an encrypted database this also closes it and forgets the key, so nothing readable (and no
    key) is left in memory until the password is entered again.
    """
    session_service.revoke_token(extract_bearer_token(authorization))
    if manager.encrypted:
        try:
            manager.close()
        except Exception:  # noqa: BLE001 - locking must never fail the caller
            log.exception("Could not close the encrypted database")


@router.post(
    "/change-password",
    response_model=SessionToken,
    dependencies=[Depends(require_unlocked)],
)
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db)) -> SessionToken:
    """Change the app lock password. All existing sessions are ended and a new one starts."""
    _check_attempts()
    _verify_or_401(db, payload.current_password, "Incorrect current password")

    if manager.encrypted:
        # The password is also the encryption key, so the file is re-keyed first; the stored hash is
        # updated only once that succeeded, on a fresh session (the engine is rebuilt).
        db.close()
        try:
            manager.change_password(payload.current_password, payload.new_password)
        except DatabaseBusyError as exc:
            raise _busy(exc) from exc
        except crypto.WrongPasswordError as exc:
            raise HTTPException(status_code=401, detail="Incorrect current password") from exc
        fresh = manager.session()
        try:
            auth_service.set_password_hash(fresh, payload.new_password)  # type: ignore[arg-type]
        finally:
            if fresh is not None:
                fresh.close()
    else:
        auth_service.set_password_hash(db, payload.new_password)

    session_service.revoke_all_tokens()
    return SessionToken(token=session_service.issue_token())


@router.post(
    "/encryption/enable",
    response_model=EncryptionResult,
    dependencies=[Depends(require_unlocked)],
)
def enable_encryption(payload: EncryptionRequest, db: Session = Depends(get_db)) -> EncryptionResult:
    """Encrypt the database file with the App Lock password."""
    _check_attempts()
    if not auth_service.is_locked(db):
        raise HTTPException(status_code=409, detail="Set an App Lock password first: it becomes the encryption key.")
    if not manager.can_encrypt:
        raise HTTPException(status_code=409, detail="Encryption is not available in this build.")
    if manager.encrypted:
        raise HTTPException(status_code=409, detail="The database is already encrypted.")
    _verify_or_401(db, payload.password)

    db.close()  # release this request's connection so the file can be swapped
    try:
        report = manager.encrypt_database(payload.password)
    except DatabaseBusyError as exc:
        raise _busy(exc) from exc
    except crypto.VerificationError as exc:
        log.error("Encryption aborted: %s", exc)
        raise HTTPException(status_code=500, detail="The encrypted copy could not be verified, so nothing was changed.") from exc
    except (OSError, RuntimeError) as exc:
        log.exception("Encryption failed")
        raise HTTPException(status_code=500, detail=f"Encryption failed and your data is unchanged: {exc}") from exc
    return EncryptionResult(encrypted=True, removed_plain_backups=report.removed_plain_backups)


@router.post(
    "/encryption/disable",
    response_model=EncryptionResult,
    dependencies=[Depends(require_unlocked)],
)
def disable_encryption(payload: EncryptionRequest, db: Session = Depends(get_db)) -> EncryptionResult:
    """Turn encryption off again, leaving a plain database."""
    _check_attempts()
    if not manager.encrypted:
        raise HTTPException(status_code=409, detail="The database is not encrypted.")
    _verify_or_401(db, payload.password)

    db.close()
    try:
        manager.decrypt_database(payload.password)
    except DatabaseBusyError as exc:
        raise _busy(exc) from exc
    except crypto.WrongPasswordError as exc:
        raise HTTPException(status_code=401, detail="Incorrect password") from exc
    except crypto.VerificationError as exc:
        log.error("Decryption aborted: %s", exc)
        raise HTTPException(status_code=500, detail="The decrypted copy could not be verified, so nothing was changed.") from exc
    except (OSError, RuntimeError) as exc:
        log.exception("Decryption failed")
        raise HTTPException(status_code=500, detail=f"Could not remove encryption and your data is unchanged: {exc}") from exc
    return EncryptionResult(encrypted=False)
