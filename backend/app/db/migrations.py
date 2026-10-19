"""Lightweight schema versioning for the local SQLite database.

`Base.metadata.create_all` creates missing tables but never alters existing ones, so a user who
upgrades TaskFlow would otherwise be stuck on the schema they first installed. This module records
a schema version in SQLite's `PRAGMA user_version` and applies numbered upgrade steps in order.

How to change the schema later:
    1. Update the models.
    2. Bump LATEST_SCHEMA_VERSION and add a function to _UPGRADES under that number that applies
       the change (e.g. `ALTER TABLE items ADD COLUMN ...`) to an *existing* database.
Brand-new databases are created from the models directly and stamped with the latest version.

Version history:
    0  Legacy databases created before versioning (items + app_settings only).
    1  Adds the tags and item_tags tables (picked up by create_all, so no ALTER needed).
    2  Adds the settings and item_embeddings tables for the optional local AI features.
"""

from collections.abc import Callable

from sqlalchemy import Connection, Engine, inspect, text

from .base import Base

LATEST_SCHEMA_VERSION = 2

# Upgrade steps for *existing* databases, keyed by the version they upgrade to. Versions 1 and 2
# only add new tables, which create_all handles, so they need no entry. Later versions that alter existing
# tables register a function here.
_UPGRADES: dict[int, Callable[[Connection], None]] = {}


def _get_version(connection: Connection) -> int:
    return connection.execute(text("PRAGMA user_version")).scalar_one()


def _set_version(connection: Connection, version: int) -> None:
    # PRAGMA does not accept bound parameters; version is always an int we control.
    connection.execute(text(f"PRAGMA user_version = {int(version)}"))


def migrate(engine: Engine) -> None:
    """Create or upgrade the schema so it matches the current models."""
    if engine.dialect.name != "sqlite":
        # Versioning relies on SQLite's user_version pragma; other databases are managed externally.
        Base.metadata.create_all(bind=engine)
        return

    is_new_database = not inspect(engine).has_table("items")

    with engine.begin() as connection:
        if is_new_database:
            Base.metadata.create_all(bind=connection)
            _set_version(connection, LATEST_SCHEMA_VERSION)
            return

        current = _get_version(connection)
        if current > LATEST_SCHEMA_VERSION:
            raise RuntimeError(
                f"This database was created by a newer version of TaskFlow "
                f"(schema {current}, this app supports up to {LATEST_SCHEMA_VERSION}). "
                "Please update TaskFlow."
            )

        for version in range(current + 1, LATEST_SCHEMA_VERSION + 1):
            upgrade = _UPGRADES.get(version)
            if upgrade is not None:
                upgrade(connection)
            # Creates any tables introduced by this version; existing tables are left untouched.
            Base.metadata.create_all(bind=connection)
            _set_version(connection, version)
