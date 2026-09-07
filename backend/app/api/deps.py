from collections.abc import Generator

from sqlalchemy.orm import Session

from ..db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for a single request, closing it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
