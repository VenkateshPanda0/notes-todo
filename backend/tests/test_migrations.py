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


def test_version_1_database_gains_the_ai_tables_and_keeps_its_data(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'v1.db'}")
    # Build a database exactly as schema version 1 shipped (tags, but no settings/embeddings).
    with engine.begin() as connection:
        for statement in filter(None, (s.strip() for s in LEGACY_SCHEMA.split(";"))):
            connection.execute(text(statement))
        connection.execute(text("CREATE TABLE tags (id INTEGER PRIMARY KEY, name VARCHAR(32) NOT NULL UNIQUE)"))
        connection.execute(
            text(
                "CREATE TABLE item_tags (item_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, "
                "PRIMARY KEY (item_id, tag_id))"
            )
        )
        connection.execute(
            text(
                "INSERT INTO items (title, content, type, completed, priority, created_at, updated_at) "
                "VALUES ('Kept', 'safe', 'NOTE', 0, 'LOW', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"
            )
        )
        connection.execute(text("PRAGMA user_version = 1"))

    init_database(engine)

    assert {"settings", "item_embeddings"} <= set(inspect(engine).get_table_names())
    assert _version(engine) == LATEST_SCHEMA_VERSION
    with engine.connect() as connection:
        assert connection.execute(text("SELECT title, content FROM items")).one() == ("Kept", "safe")
    engine.dispose()


def _columns(engine, table: str) -> set[str]:
    with engine.connect() as connection:
        return {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})"))}


def test_every_old_version_gains_the_recurrence_columns_and_keeps_its_rows(legacy_engine):
    # legacy_engine is a version-0 database with one todo in it.
    assert "recurrence" not in _columns(legacy_engine, "items")

    init_database(legacy_engine)

    assert {"recurrence", "recurrence_day"} <= _columns(legacy_engine, "items")
    with legacy_engine.connect() as connection:
        row = connection.execute(text("SELECT title, priority, recurrence, recurrence_day FROM items")).one()
    assert tuple(row) == ("Old todo", "HIGH", None, None)  # existing todos simply don't repeat


def test_version_2_database_is_altered_in_place(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'v2.db'}")
    with engine.begin() as connection:
        for statement in filter(None, (s.strip() for s in LEGACY_SCHEMA.split(";"))):
            connection.execute(text(statement))
        connection.execute(text("CREATE TABLE tags (id INTEGER PRIMARY KEY, name VARCHAR(32) NOT NULL UNIQUE)"))
        connection.execute(text("CREATE TABLE item_tags (item_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY (item_id, tag_id))"))
        connection.execute(text("CREATE TABLE settings (key VARCHAR(64) PRIMARY KEY, value TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE item_embeddings (item_id INTEGER PRIMARY KEY, model VARCHAR(128) NOT NULL, text_hash VARCHAR(64) NOT NULL, vector TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO items (title, content, type, completed, priority, created_at, updated_at) VALUES ('Keep', 'me', 'TODO', 1, 'LOW', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"))
        connection.execute(text("INSERT INTO settings (key, value) VALUES ('ai_enabled', '1')"))
        connection.execute(text("PRAGMA user_version = 2"))

    init_database(engine)

    assert _version(engine) == LATEST_SCHEMA_VERSION
    with engine.connect() as connection:
        assert tuple(connection.execute(text("SELECT title, content, completed FROM items")).one()) == ("Keep", "me", 1)
        assert connection.execute(text("SELECT value FROM settings WHERE key='ai_enabled'")).scalar_one() == "1"
    engine.dispose()


def test_add_columns_is_safe_to_run_twice(legacy_engine):
    from backend.app.db.migrations import _add_columns

    with legacy_engine.begin() as connection:
        _add_columns(connection, "items", {"extra": "TEXT"})
        _add_columns(connection, "items", {"extra": "TEXT"})  # must not raise "duplicate column"

    assert "extra" in _columns(legacy_engine, "items")


# --- safety copy before an upgrade ----------------------------------------------------------------


def _file_legacy_engine(tmp_path):
    (tmp_path / "data").mkdir()
    engine = create_engine(f"sqlite:///{tmp_path / 'data' / 'flow.db'}")
    with engine.begin() as connection:
        for statement in filter(None, (s.strip() for s in LEGACY_SCHEMA.split(";"))):
            connection.execute(text(statement))
        connection.execute(text(
            "INSERT INTO items (title, content, type, completed, priority, created_at, updated_at) "
            "VALUES ('Precious', 'data', 'NOTE', 0, 'LOW', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"))
    return engine


def test_upgrading_an_existing_database_first_saves_a_copy_of_the_old_file(tmp_path):
    import sqlite3

    engine = _file_legacy_engine(tmp_path)

    init_database(engine)

    copies = list((tmp_path / "data" / "backups").glob("before-upgrade-v0-*.db"))
    assert len(copies) == 1
    old = sqlite3.connect(copies[0])
    try:
        # The copy is the database as it was BEFORE the upgrade: old schema, original data.
        assert "recurrence" not in [r[1] for r in old.execute("PRAGMA table_info(items)")]
        assert old.execute("SELECT title FROM items").fetchone() == ("Precious",)
        assert old.execute("PRAGMA user_version").fetchone()[0] == 0
    finally:
        old.close()
    assert "recurrence" in _columns(engine, "items")  # ...while the live database was upgraded
    engine.dispose()


def test_no_copy_is_made_when_nothing_needs_upgrading(tmp_path):
    engine = _file_legacy_engine(tmp_path)
    init_database(engine)
    init_database(engine)
    init_database(engine)

    assert len(list((tmp_path / "data" / "backups").glob("before-upgrade-*.db"))) == 1


def test_brand_new_databases_need_no_upgrade_copy(tmp_path):
    (tmp_path / "data").mkdir()
    engine = create_engine(f"sqlite:///{tmp_path / 'data' / 'flow.db'}")

    init_database(engine)

    assert not (tmp_path / "data" / "backups").exists()
    engine.dispose()


def test_a_failed_copy_does_not_block_the_upgrade(tmp_path, monkeypatch):
    from backend.app.services import backup as backup_service

    engine = _file_legacy_engine(tmp_path)
    monkeypatch.setattr(backup_service, "snapshot_database", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))

    init_database(engine)

    assert "recurrence" in _columns(engine, "items")
    engine.dispose()


def test_only_the_newest_upgrade_copies_are_kept(tmp_path):
    from datetime import datetime

    from backend.app.services import backup as backup_service

    engine = _file_legacy_engine(tmp_path)
    for minute in range(5):
        backup_service.snapshot_before_upgrade(engine, 1, now=datetime(2026, 3, 5, 12, minute, 0))

    names = sorted(p.name for p in (tmp_path / "data" / "backups").glob("before-upgrade-*.db"))
    assert names == [f"before-upgrade-v1-20260305-12{m:02d}00.db" for m in (2, 3, 4)]
    listed = [b.name for b in backup_service.list_auto_backups(engine)]
    assert set(listed) == set(names)  # and they show up in the backups list
    engine.dispose()


def test_in_memory_databases_skip_the_copy_without_error():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for statement in filter(None, (s.strip() for s in LEGACY_SCHEMA.split(";"))):
            connection.execute(text(statement))

    init_database(engine)

    assert "recurrence" in _columns(engine, "items")
