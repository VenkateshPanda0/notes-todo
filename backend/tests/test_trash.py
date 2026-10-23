import io
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text

from backend.app.db.migrations import LATEST_SCHEMA_VERSION
from backend.app.db.session import init_database
from backend.app.services import items as items_service


def make(client, title="Thing", type="NOTE", **extra):
    response = client.post("/api/items", json={"title": title, "type": type, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def titles(client, **params):
    return sorted(i["title"] for i in client.get("/api/items", params=params).json())


def trash(client):
    return client.get("/api/items/trash").json()


# --- deleting moves to the Trash -----------------------------------------------------------------


def test_deleting_hides_the_item_everywhere_and_puts_it_in_the_trash(client):
    item = make(client, "Gone", content="body", tags=["t"])

    assert client.delete(f"/api/items/{item['id']}").status_code == 204

    assert client.get(f"/api/items/{item['id']}").status_code == 404
    assert titles(client) == []
    assert [i["title"] for i in trash(client)] == ["Gone"]
    assert trash(client)[0]["deleted_at"] is not None


def test_a_trashed_item_cannot_be_changed_or_completed(client):
    item = make(client, "Gone", type="TODO")
    client.delete(f"/api/items/{item['id']}")

    assert client.patch(f"/api/items/{item['id']}", json={"title": "x"}).status_code == 404
    assert client.post(f"/api/items/{item['id']}/complete").status_code == 404
    assert client.post(f"/api/items/{item['id']}/reopen").status_code == 404
    assert client.post(f"/api/items/{item['id']}/convert").status_code == 404
    assert client.get(f"/api/items/{item['id']}/backlinks").status_code == 404


def test_deleting_twice_or_deleting_a_missing_item_is_a_404(client):
    item = make(client)
    client.delete(f"/api/items/{item['id']}")

    assert client.delete(f"/api/items/{item['id']}").status_code == 404
    assert client.delete("/api/items/9999").status_code == 404


def test_live_items_have_no_deleted_at(client):
    assert make(client)["deleted_at"] is None


def test_the_trash_lists_the_most_recently_deleted_first(client):
    a, b, c = make(client, "A"), make(client, "B"), make(client, "C")
    for item in (b, a, c):
        client.delete(f"/api/items/{item['id']}")

    assert [i["title"] for i in trash(client)] == ["C", "A", "B"]


# --- restoring -----------------------------------------------------------------------------------


def test_restoring_brings_back_the_same_item_with_everything(client):
    item = make(client, "Keep me", type="TODO", priority="HIGH", due_date="2026-12-01", recurrence="1w",
                tags=["alpha"], content="details")
    client.delete(f"/api/items/{item['id']}")

    response = client.post(f"/api/items/{item['id']}/restore")
    restored = client.get(f"/api/items/{item['id']}").json()

    assert response.status_code == 200 and response.json()["deleted_at"] is None
    assert {k: restored[k] for k in ("id", "title", "content", "priority", "due_date", "recurrence", "tags")} == {
        k: item[k] for k in ("id", "title", "content", "priority", "due_date", "recurrence", "tags")}
    assert trash(client) == [] and titles(client) == ["Keep me"]


def test_restoring_something_not_in_the_trash_or_unknown_is_a_404(client):
    item = make(client)

    assert client.post(f"/api/items/{item['id']}/restore").status_code == 404
    assert client.post("/api/items/9999/restore").status_code == 404


# --- permanent deletion --------------------------------------------------------------------------


def test_permanent_delete_only_works_on_trashed_items(client):
    live, gone = make(client, "Live"), make(client, "Gone")
    client.delete(f"/api/items/{gone['id']}")

    assert client.delete(f"/api/items/{live['id']}/permanent").status_code == 404  # a safety catch
    assert titles(client) == ["Live"]
    assert client.delete(f"/api/items/{gone['id']}/permanent").status_code == 204
    assert trash(client) == []
    assert client.post(f"/api/items/{gone['id']}/restore").status_code == 404  # truly gone


def test_emptying_the_trash_deletes_only_trashed_items_and_reports_how_many(client):
    keep = make(client, "Keep", tags=["live"])
    for name in ("x", "y", "z"):
        item = make(client, name, tags=["bin"])
        client.delete(f"/api/items/{item['id']}")

    response = client.delete("/api/items/trash")

    assert response.json() == {"deleted": 3}
    assert trash(client) == [] and titles(client) == ["Keep"]
    assert client.get("/api/tags").json() == [{"name": "live", "count": 1}]
    assert client.delete("/api/items/trash").json() == {"deleted": 0}
    assert keep["id"]


# --- expiry --------------------------------------------------------------------------------------


def test_items_are_purged_after_30_days_but_not_before(client, db_session_factory, monkeypatch):
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(items_service, "_now", lambda: now)
    old, recent, edge = make(client, "old"), make(client, "recent"), make(client, "edge")
    with db_session_factory() as db:
        for item_id, age in ((old["id"], 31), (recent["id"], 29), (edge["id"], 30)):
            db.execute(text("UPDATE items SET deleted_at = :d WHERE id = :i"),
                       {"d": (now - timedelta(days=age) + timedelta(minutes=1 if age == 30 else 0)).replace(tzinfo=None), "i": item_id})
        db.commit()

        purged = items_service.purge_expired_trash(db)

    assert purged == 1
    assert sorted(i["title"] for i in trash(client)) == ["edge", "recent"]


def test_purging_nothing_when_the_trash_is_empty(client, db_session_factory):
    with db_session_factory() as db:
        assert items_service.purge_expired_trash(db) == 0


# --- the Trash must not leak into any other feature ----------------------------------------------


def test_trashed_items_do_not_count_toward_tags_or_tag_filters(client):
    a = make(client, "A", tags=["shared", "only-a"])
    make(client, "B", tags=["shared"])
    client.delete(f"/api/items/{a['id']}")

    assert client.get("/api/tags").json() == [{"name": "shared", "count": 1}]
    assert titles(client, tag="only-a") == []
    assert titles(client, tag="shared") == ["B"]
    client.post(f"/api/items/{a['id']}/restore")
    assert client.get("/api/tags").json() == [{"name": "only-a", "count": 1}, {"name": "shared", "count": 2}]


def test_trashed_items_disappear_from_the_graph_and_links_to_them_become_placeholders(client):
    target = make(client, "Target")
    make(client, "Source", content="see [[Target]]")
    make(client, "Trashed source", content="also [[Target]]")
    client.delete(f"/api/items/{target['id']}")
    trashed_source = next(i for i in client.get("/api/items").json() if i["title"] == "Trashed source")
    client.delete(f"/api/items/{trashed_source['id']}")

    graph = client.get("/api/graph").json()

    nodes = {n["title"]: n for n in graph["nodes"]}
    assert set(nodes) == {"Source", "Target"}
    assert nodes["Target"]["missing"] is True  # the live note's link now points at nothing
    assert len(graph["edges"]) == 1


def test_trashed_notes_are_not_backlinks(client):
    target = make(client, "Target")
    live = make(client, "Live", content="[[Target]]")
    trashed = make(client, "Trashed", content="[[Target]]")
    client.delete(f"/api/items/{trashed['id']}")

    assert [i["title"] for i in client.get(f"/api/items/{target['id']}/backlinks").json()] == ["Live"]
    assert live["id"]


def test_exports_leave_out_the_trash(client):
    make(client, "Visible")
    gone = make(client, "Hidden-in-trash")
    client.delete(f"/api/items/{gone['id']}")

    exported = client.get("/api/backup/export.json").json()
    archive = zipfile.ZipFile(io.BytesIO(client.get("/api/backup/export.zip").content))

    assert [i["title"] for i in exported["items"]] == ["Visible"]
    assert archive.namelist() == ["Notes/Visible.md"]


def test_importing_an_item_that_matches_a_trashed_one_still_adds_it(client):
    gone = make(client, "Same", content="x")
    client.delete(f"/api/items/{gone['id']}")
    payload = {"format": "taskflow-export", "version": 1, "items": [{"title": "Same", "type": "NOTE", "content": "x"}]}

    result = client.post("/api/backup/import?mode=merge", json=payload).json()

    assert result["imported"] == 1 and titles(client) == ["Same"]


def test_replace_import_empties_the_trash_too(client):
    gone = make(client, "Old")
    client.delete(f"/api/items/{gone['id']}")
    payload = {"format": "taskflow-export", "version": 1, "items": [{"title": "New", "type": "NOTE"}]}

    client.post("/api/backup/import?mode=replace", json=payload)

    assert trash(client) == [] and titles(client) == ["New"]


def test_a_trashed_occurrence_does_not_block_the_next_one_of_a_series(client):
    from backend.app.services import items as svc

    original = make(client, "Water plants", type="TODO", due_date="2026-10-21", recurrence="1w")
    # A previous completion already produced next week's occurrence, which the user then trashed.
    pinned = date(2026, 10, 21)
    svc._today = lambda: pinned  # type: ignore[assignment]
    try:
        client.post(f"/api/items/{original['id']}/complete")
        spawned = next(i for i in client.get("/api/items").json() if not i["completed"])
        client.delete(f"/api/items/{spawned['id']}")
        client.post(f"/api/items/{original['id']}/reopen")

        client.post(f"/api/items/{original['id']}/complete")
    finally:
        svc._today = lambda: date.today()  # type: ignore[assignment]

    open_items = [i for i in client.get("/api/items").json() if not i["completed"]]
    assert len(open_items) == 1 and open_items[0]["due_date"] == "2026-10-28"


# --- access control and the migration ------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/items/trash"), ("delete", "/api/items/trash"), ("post", "/api/items/1/restore"),
     ("delete", "/api/items/1/permanent")],
)
def test_trash_routes_require_the_session_when_locked(client, method, path):
    client.post("/api/auth/setup", json={"password": "secret1"})

    assert getattr(client, method)(path).status_code == 401


def test_a_version_3_database_gains_deleted_at_and_nothing_is_deleted(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'v3.db'}")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE items (id INTEGER NOT NULL PRIMARY KEY, title VARCHAR(255) NOT NULL, content TEXT NOT NULL, "
            "type VARCHAR(4) NOT NULL, completed BOOLEAN NOT NULL, priority VARCHAR(6) NOT NULL, due_date DATE, "
            "recurrence VARCHAR(16), recurrence_day INTEGER, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL)"))
        connection.execute(text("CREATE TABLE app_settings (id INTEGER NOT NULL PRIMARY KEY, password_hash VARCHAR(255) NOT NULL)"))
        connection.execute(text("CREATE TABLE tags (id INTEGER PRIMARY KEY, name VARCHAR(32) NOT NULL UNIQUE)"))
        connection.execute(text("CREATE TABLE item_tags (item_id INTEGER NOT NULL, tag_id INTEGER NOT NULL, PRIMARY KEY (item_id, tag_id))"))
        connection.execute(text("CREATE TABLE settings (key VARCHAR(64) PRIMARY KEY, value TEXT NOT NULL)"))
        connection.execute(text("CREATE TABLE item_embeddings (item_id INTEGER PRIMARY KEY, model VARCHAR(128) NOT NULL, text_hash VARCHAR(64) NOT NULL, vector TEXT NOT NULL)"))
        connection.execute(text("INSERT INTO items (title, content, type, completed, priority, created_at, updated_at) VALUES ('Existing', 'x', 'NOTE', 0, 'LOW', '2026-01-01 00:00:00', '2026-01-01 00:00:00')"))
        connection.execute(text("PRAGMA user_version = 3"))

    init_database(engine)

    with engine.connect() as connection:
        columns = {row[1] for row in connection.execute(text("PRAGMA table_info(items)"))}
        row = connection.execute(text("SELECT title, deleted_at FROM items")).one()
        version = connection.execute(text("PRAGMA user_version")).scalar_one()
    assert "deleted_at" in columns and tuple(row) == ("Existing", None) and version == LATEST_SCHEMA_VERSION == 4
    engine.dispose()
