import os
import sys

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from .base import Base


def default_database_url() -> str:
    """Pick a sensible default DB location: a per-user app-data folder when
    running as a packaged exe, or a local file next to the source when
    running from source during development."""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built exe: use a proper writable, stable
        # location instead of wherever the exe happens to be launched from.
        app_data_dir = os.path.join(os.environ["APPDATA"], "TaskFlow")
        os.makedirs(app_data_dir, exist_ok=True)
        db_path = os.path.join(app_data_dir, "flow.db")
        return f"sqlite:///{db_path}"

    return "sqlite:///./flow.db"


DATABASE_URL = default_database_url()

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database(database_engine: Engine | None = None) -> None:
    """Create the current schema for a supplied engine or the local database."""
    from ..models import AppSettings, Item  # noqa: F401

    Base.metadata.create_all(bind=database_engine or engine)
