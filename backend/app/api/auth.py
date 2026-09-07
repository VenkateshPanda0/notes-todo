from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..schemas.auth import (
    ChangePasswordRequest,
    LockStatus,
    SetPasswordRequest,
    UnlockRequest,
)
from ..services import auth as auth_service
from ..services.auth import (
    IncorrectPasswordError,
    NoPasswordSetError,
    PasswordAlreadySetError,
)
from .deps import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status", response_model=LockStatus)
def get_lock_status(db: Session = Depends(get_db)) -> LockStatus:
    """Report whether the app currently has a password lock configured."""
    return LockStatus(is_locked=auth_service.is_locked(db))


@router.post("/setup", status_code=204)
def setup_password(payload: SetPasswordRequest, db: Session = Depends(get_db)) -> None:
    """Configure the app lock password for the first time."""
    try:
        auth_service.set_password(db, payload.password)
    except PasswordAlreadySetError as exc:
        raise HTTPException(status_code=409, detail="Password already set") from exc


@router.post("/unlock", status_code=204)
def unlock(payload: UnlockRequest, db: Session = Depends(get_db)) -> None:
    """Verify the app lock password."""
    try:
        auth_service.unlock(db, payload.password)
    except NoPasswordSetError as exc:
        raise HTTPException(status_code=409, detail="No password configured") from exc
    except IncorrectPasswordError as exc:
        raise HTTPException(status_code=401, detail="Incorrect password") from exc


@router.post("/change-password", status_code=204)
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db)) -> None:
    """Change the app lock password."""
    try:
        auth_service.change_password(db, payload.current_password, payload.new_password)
    except NoPasswordSetError as exc:
        raise HTTPException(status_code=409, detail="No password configured") from exc
    except IncorrectPasswordError as exc:
        raise HTTPException(status_code=401, detail="Incorrect current password") from exc
