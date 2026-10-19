import pytest
from sqlalchemy import create_engine, inspect, text

from backend.app.db.migrations import LATEST_SCHEMA_VERSION, migrate
from backend.app.db.session import init_database

# The items/app_settings tables exactly as shipped before schema versioning and tags existed.
LEGACY_SCHEMA = """
CREATE TABLE items (
    id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(4) NOT NULL,
    completed BOOLEAN NOT NULL,
    priority VARCHAR(6) NOT NULL,
    due_date DATE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);
CREATE TABLE app_settings (id INTEGER NOT NULL PRIMARY KEY, password_hash VARCHAR(255) NOT NULL);
"""


def _version(engine) -> int:
    with engine.connect() as connection:
        return connection.execute(text("PRAGMA user_version")).scalar_one()


@pytest.fixture()
def legacy_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        for statement in filter(None, (s.strip() for s in LEGACY_SCHEMA.split(";"))):
            connection.execute(text(statement))
        connection.execute(
            text(
                "INSERT INTO items (title, content, type, completed, priority, due_date, "
                "created_at, updated_at) VALUES ('Old todo', 'keep me', 'TODO', 0, 'HIGH', "
                "'2026-01-02', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        )
        connection.execute(text("INSERT INTO app_settings (id, password_hash) VALUES (1, 'abc$def')"))
    yield engine
    engine.dispose()


def test_new_database_is_created_and_stamped_with_the_latest_version():
    engine = create_engine("sqlite://")

    init_database(engine)

    assert {"items", "tags", "item_tags", "app_settings"} <= set(inspect(engine).get_table_names())
    assert _version(engine) == LATEST_SCHEMA_VERSION


def test_legacy_database_is_upgraded_without_losing_data(legacy_engine):
    assert _version(legacy_engine) == 0

    init_database(legacy_engine)

    assert {"tags", "item_tags"} <= set(inspect(legacy_engine).get_table_names())
    assert _version(legacy_engine) == LATEST_SCHEMA_VERSION
    with legacy_engine.connect() as connection:
        row = connection.execute(text("SELECT title, content, priority, due_date FROM items")).one()
        lock = connection.execute(text("SELECT password_hash FROM app_settings")).scalar_one()
    assert tuple(row) == ("Old todo", "keep me", "HIGH", "2026-01-02")
    assert lock == "abc$def"


def test_upgrade_is_idempotent(legacy_engine):
    init_database(legacy_engine)
    init_database(legacy_engine)

    assert _version(legacy_engine) == LATEST_SCHEMA_VERSION
    with legacy_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM items")).scalar_one() == 1


def test_database_from_a_newer_app_version_is_refused(legacy_engine):
    with legacy_engine.begin() as connection:
        connection.execute(text(f"PRAGMA user_version = {LATEST_SCHEMA_VERSION + 1}"))

    with pytest.raises(RuntimeError, match="newer version"):
        migrate(legacy_engine)

    with legacy_engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM items")).scalar_one() == 1
