import os
import sys

from sqlalchemy import Engine

from .manager import manager
from .migrations import migrate, needs_upgrade


def app_data_dir() -> str:
    """Per-user folder where the packaged app keeps its data, created if missing.

    Windows keeps the original %APPDATA%\\TaskFlow location so existing users' data is found.
    TASKFLOW_DATA_DIR overrides everything (useful for tests and portable installs).
    """
    override = os.getenv("TASKFLOW_DATA_DIR")
    if override:
        path = override
    elif sys.platform == "win32":
        roaming = os.environ.get("APPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming"
        )
        path = os.path.join(roaming, "TaskFlow")
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "TaskFlow")
    else:
        data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(
            os.path.expanduser("~"), ".local", "share"
        )
        path = os.path.join(data_home, "taskflow")
    os.makedirs(path, exist_ok=True)
    return path


def default_database_url() -> str:
    """Pick a sensible default DB location: a per-user app-data folder when
    running as a packaged exe, or a local file next to the source when
    running from source during development."""
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    if getattr(sys, "frozen", False):
        # Running as a PyInstaller-built exe: use a proper writable, stable
        # location instead of wherever the exe happens to be launched from.
        return f"sqlite:///{os.path.join(app_data_dir(), 'flow.db')}"

    return "sqlite:///./flow.db"


DATABASE_URL = default_database_url()
manager.configure(DATABASE_URL)


def init_database(database_engine: Engine | None = None) -> None:
    """Create or upgrade the schema for a supplied engine or the managed database."""
    from ..models import AppSettings, Item, ItemEmbedding, Setting, Tag  # noqa: F401  (register models)

    target = database_engine or manager.engine
    if target is None:
        raise RuntimeError("The database is locked.")
    behind = needs_upgrade(target)
    if behind is not None:
        # Copy the file first so a failed upgrade can never cost a user their data.
        from ..services.backup import snapshot_before_upgrade

        snapshot_before_upgrade(target, behind)
    migrate(target)
