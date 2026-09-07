import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from .base import Base


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./flow.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database(database_engine: Engine | None = None) -> None:
    """Create the current schema for a supplied engine or the local database."""
    from ..models import Item  # noqa: F401

    Base.metadata.create_all(bind=database_engine or engine)
