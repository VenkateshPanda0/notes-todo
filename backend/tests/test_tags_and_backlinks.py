from datetime import date

import pytest

from backend.app.services.quick_add import parse_quick_add
from backend.app.services.tags import normalize_tags


def make(client, title, type="NOTE", **extra):
    response = client.post("/api/items", json={"title": title, "type": type, **extra})
    assert response.status_code == 201, response.text
    return response.json()


# --- tag normalization -------------------------------------------------------------------------


def test_normalize_tags_lowercases_strips_hash_and_dedupes():
    assert normalize_tags(["#Work", "work", " Home ", "", "#"]) == ["work", "home"]


@pytest.mark.parametrize("bad", ["1abc", "has space", "bad!", "-start", "x" * 33])
def test_normalize_tags_rejects_invalid_names(bad):
    with pytest.raises(ValueError):
        normalize_tags([bad])


def test_normalize_tags_caps_the_count():
    with pytest.raises(ValueError):
        normalize_tags([f"t{i}" for i in range(21)])


# --- tags through the API ----------------------------------------------------------------------


def test_items_default_to_no_tags(client):
    assert make(client, "plain")["tags"] == []


def test_create_item_with_tags_normalizes_them(client):
    item = make(client, "trip", tags=["#Travel", "plans", "travel"])

    assert item["tags"] == ["plans", "travel"]  # sorted by name, de-duplicated, lowercased


def test_invalid_tag_is_a_422(client):
    response = client.post("/api/items", json={"title": "x", "type": "NOTE", "tags": ["bad tag"]})

    assert response.status_code == 422


def test_update_replaces_tags_and_omitting_tags_leaves_them(client):
    item = make(client, "x", tags=["a", "b"])

    renamed = client.patch(f"/api/items/{item['id']}", json={"title": "y"}).json()
    replaced = client.patch(f"/api/items/{item['id']}", json={"tags": ["c"]}).json()
    cleared = client.patch(f"/api/items/{item['id']}", json={"tags": []}).json()

    assert renamed["tags"] == ["a", "b"]
    assert replaced["tags"] == ["c"]
    assert cleared["tags"] == []


def test_tag_rows_are_shared_between_items(client):
    make(client, "one", tags=["shared"])
    make(client, "two", tags=["shared"])

    assert client.get("/api/tags").json() == [{"name": "shared", "count": 2}]


def test_tags_endpoint_lists_only_tags_in_use_with_counts(client):
    a = make(client, "a", tags=["alpha", "beta"])
    make(client, "b", tags=["beta"])
    client.patch(f"/api/items/{a['id']}", json={"tags": ["beta"]})  # alpha is no longer used

    assert client.get("/api/tags").json() == [{"name": "beta", "count": 2}]


def test_deleting_an_item_removes_its_tag_usage(client):
    item = make(client, "gone", tags=["temp"])
    client.delete(f"/api/items/{item['id']}")

    assert client.get("/api/tags").json() == []


def test_filter_items_by_tag(client):
    make(client, "tagged", tags=["work"])
    make(client, "other", tags=["home"])
    make(client, "none")

    titles = [i["title"] for i in client.get("/api/items", params={"tag": "work"}).json()]
    hashed = [i["title"] for i in client.get("/api/items", params={"tag": "#WORK"}).json()]

    assert titles == ["tagged"]
    assert hashed == ["tagged"]


def test_tag_filter_combines_with_type_filter(client):
    make(client, "note", type="NOTE", tags=["x"])
    make(client, "todo", type="TODO", tags=["x"])

    items = client.get("/api/items", params={"tag": "x", "type": "NOTE"}).json()

    assert [i["title"] for i in items] == ["note"]


def test_converting_an_item_keeps_its_tags(client):
    item = make(client, "keep", type="TODO", tags=["x"])

    converted = client.post(f"/api/items/{item['id']}/convert").json()

    assert converted["tags"] == ["x"]


def test_tags_endpoint_requires_the_session_when_locked(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    assert client.get("/api/tags").status_code == 401


# --- backlinks ---------------------------------------------------------------------------------


def test_backlinks_find_items_that_link_by_title(client):
    target = make(client, "Project Atlas")
    make(client, "Meeting", content="Discussed [[Project Atlas]] timeline")
    make(client, "Aliased", content="See [[project atlas|the atlas plan]] for context")
    make(client, "Unrelated", content="mentions Project Atlas without brackets")

    titles = {i["title"] for i in client.get(f"/api/items/{target['id']}/backlinks").json()}

    assert titles == {"Meeting", "Aliased"}


def test_backlinks_exclude_the_item_itself(client):
    target = make(client, "Loop", content="links to [[Loop]]")

    assert client.get(f"/api/items/{target['id']}/backlinks").json() == []


def test_backlinks_treat_like_wildcards_literally(client):
    target = make(client, "100%_done")
    make(client, "yes", content="see [[100%_done]]")
    other = make(client, "no", content="see [[100xxdone]]")

    titles = [i["title"] for i in client.get(f"/api/items/{target['id']}/backlinks").json()]

    assert titles == ["yes"]
    assert other["title"] not in titles


def test_backlinks_work_between_todos_and_notes(client):
    target = make(client, "Pay rent", type="TODO")
    make(client, "Budget", type="NOTE", content="[[Pay rent]] is due first")

    items = client.get(f"/api/items/{target['id']}/backlinks").json()

    assert [i["title"] for i in items] == ["Budget"]


def test_backlinks_for_missing_item_is_404(client):
    assert client.get("/api/items/999/backlinks").status_code == 404


def test_backlinks_require_the_session_when_locked(client):
    target = make(client, "t")
    client.post("/api/auth/setup", json={"password": "secret1"})

    assert client.get(f"/api/items/{target['id']}/backlinks").status_code == 401


# --- quick add ---------------------------------------------------------------------------------


def test_quick_add_extracts_tags_and_removes_them_from_the_title():
    r = parse_quick_add("plan trip #Travel tomorrow #family", today=date(2026, 10, 14))

    assert r.title == "plan trip"
    assert r.tags == ("travel", "family")
    assert r.due_date == date(2026, 10, 15)


@pytest.mark.parametrize("text", ["fix bug #123", "email#nope", "see issue #1 and #2"])
def test_quick_add_leaves_numeric_and_embedded_hashes_alone(text):
    r = parse_quick_add(text)

    assert r.title == text
    assert r.tags == ()


def test_quick_add_dedupes_tags():
    assert parse_quick_add("idea #a #A #a").tags == ("a",)


def test_parse_endpoint_returns_tags(client):
    body = client.post("/api/items/parse", json={"text": "write post #blog !low"}).json()

    assert body["title"] == "write post"
    assert body["tags"] == ["blog"]
    assert body["priority"] == "LOW"
