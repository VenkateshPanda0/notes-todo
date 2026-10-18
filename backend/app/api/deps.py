from collections.abc import Generator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from ..db.session import SessionLocal
from ..services import auth as auth_service
from ..services import session as session_service


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for a single request, closing it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def extract_bearer_token(authorization: str | None) -> str | None:
    """Return the token from an `Authorization: Bearer <token>` header, if present."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token.strip()


def require_unlocked(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    """Reject the request unless the app has no lock or the caller holds a valid session token."""
    if not auth_service.is_locked(db):
        return
    if not session_service.is_valid_token(extract_bearer_token(authorization)):
        raise HTTPException(
            status_code=401,
            detail="App is locked",
            headers={"WWW-Authenticate": "Bearer"},
        )
