from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..schemas.auth import (
    ChangePasswordRequest,
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

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _too_many_attempts(exc: TooManyAttemptsError) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"Too many failed attempts. Try again in {exc.retry_after} seconds.",
        headers={"Retry-After": str(exc.retry_after)},
    )


@router.get("/status", response_model=LockStatus)
def get_lock_status(db: Session = Depends(get_db)) -> LockStatus:
    """Report whether the app currently has a password lock configured."""
    return LockStatus(is_locked=auth_service.is_locked(db))


@router.post("/setup", response_model=SessionToken)
def setup_password(payload: SetPasswordRequest, db: Session = Depends(get_db)) -> SessionToken:
    """Configure the app lock password for the first time and start a session."""
    try:
        auth_service.set_password(db, payload.password)
    except PasswordAlreadySetError as exc:
        raise HTTPException(status_code=409, detail="Password already set") from exc
    return SessionToken(token=session_service.issue_token())


@router.post("/unlock", response_model=SessionToken)
def unlock(payload: UnlockRequest, db: Session = Depends(get_db)) -> SessionToken:
    """Verify the app lock password and start a session."""
    try:
        session_service.check_attempts_allowed()
    except TooManyAttemptsError as exc:
        raise _too_many_attempts(exc) from exc

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
    """End the current session so the app must be unlocked again."""
    session_service.revoke_token(extract_bearer_token(authorization))


@router.post(
    "/change-password",
    response_model=SessionToken,
    dependencies=[Depends(require_unlocked)],
)
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db)) -> SessionToken:
    """Change the app lock password. All existing sessions are ended and a new one starts."""
    try:
        session_service.check_attempts_allowed()
    except TooManyAttemptsError as exc:
        raise _too_many_attempts(exc) from exc

    try:
        auth_service.change_password(db, payload.current_password, payload.new_password)
    except NoPasswordSetError as exc:
        raise HTTPException(status_code=409, detail="No password configured") from exc
    except IncorrectPasswordError as exc:
        session_service.record_failed_attempt()
        raise HTTPException(status_code=401, detail="Incorrect current password") from exc

    session_service.record_successful_attempt()
    session_service.revoke_all_tokens()
    return SessionToken(token=session_service.issue_token())
