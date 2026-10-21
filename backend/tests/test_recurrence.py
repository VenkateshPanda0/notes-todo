from datetime import date

import pytest

from backend.app.services import items as items_service
from backend.app.services.quick_add import parse_quick_add
from backend.app.services.recurrence import (
    advance,
    anchor_for,
    describe_recurrence,
    next_due_date,
    normalize_recurrence,
)

# --- rule parsing --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [
        ("daily", "1d"), ("Weekly", "1w"), (" MONTHLY ", "1m"), ("yearly", "1y"), ("annually", "1y"),
        ("weekdays", "weekdays"), ("every weekday", "weekdays"),
        ("3d", "3d"), ("2W", "2w"), ("12m", "12m"), ("1y", "1y"),
        (None, None), ("", None), ("none", None), ("Never", None),
    ],
)
def test_normalize_recurrence(raw, canonical):
    assert normalize_recurrence(raw) == canonical


@pytest.mark.parametrize("bad", ["0d", "d", "w2", "every day", "1x", "1000d", "-1w", "fortnightly", "1.5w"])
def test_invalid_rules_are_rejected(bad):
    with pytest.raises(ValueError):
        normalize_recurrence(bad)


@pytest.mark.parametrize(
    ("rule", "text"),
    [(None, "Does not repeat"), ("1d", "Daily"), ("1w", "Weekly"), ("1m", "Monthly"), ("1y", "Yearly"),
     ("weekdays", "Every weekday"), ("3d", "Every 3 days"), ("2w", "Every 2 weeks"), ("6m", "Every 6 months")],
)
def test_describe(rule, text):
    assert describe_recurrence(rule) == text


# --- date maths ----------------------------------------------------------------------------------


def test_simple_intervals():
    d = date(2026, 3, 10)
    assert advance(d, "1d") == date(2026, 3, 11)
    assert advance(d, "10d") == date(2026, 3, 20)
    assert advance(d, "1w") == date(2026, 3, 17)
    assert advance(d, "2w") == date(2026, 3, 24)
    assert advance(d, "1m") == date(2026, 4, 10)
    assert advance(d, "1y") == date(2027, 3, 10)


@pytest.mark.parametrize(
    ("start", "expected"),
    [
        (date(2026, 10, 19), date(2026, 10, 20)),  # Mon -> Tue
        (date(2026, 10, 23), date(2026, 10, 26)),  # Fri -> Mon
        (date(2026, 10, 24), date(2026, 10, 26)),  # Sat -> Mon
        (date(2026, 10, 25), date(2026, 10, 26)),  # Sun -> Mon
    ],
)
def test_weekdays_skip_the_weekend(start, expected):
    assert advance(start, "weekdays") == expected


def test_month_end_dates_do_not_drift():
    due, seen = date(2026, 1, 31), []
    for _ in range(5):
        due = advance(due, "1m", 31)
        seen.append(due)
    assert seen == [date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30), date(2026, 5, 31), date(2026, 6, 30)]


def test_month_end_without_an_anchor_clamps_but_would_drift():
    # This is why the anchor day is stored.
    assert advance(advance(date(2026, 1, 31), "1m"), "1m") == date(2026, 3, 28)


def test_leap_day_yearly_series():
    due = date(2024, 2, 29)
    due = advance(due, "1y", 29)
    assert due == date(2025, 2, 28)
    due = advance(advance(advance(due, "1y", 29), "1y", 29), "1y", 29)
    assert due == date(2028, 2, 29)


def test_month_arithmetic_crosses_years():
    assert advance(date(2026, 11, 15), "3m") == date(2027, 2, 15)
    assert advance(date(2026, 12, 31), "1m", 31) == date(2027, 1, 31)
    assert advance(date(2026, 1, 31), "13m", 31) == date(2027, 2, 28)


def test_anchor_only_for_months_and_years():
    assert anchor_for(date(2026, 1, 31), "1m") == 31
    assert anchor_for(date(2026, 2, 28), "1y") == 28
    assert anchor_for(date(2026, 1, 31), "1w") is None
    assert anchor_for(None, "1m") is None
    assert anchor_for(date(2026, 1, 31), None) is None


def test_next_due_date_counts_from_the_due_date_not_from_today():
    assert next_due_date(date(2026, 10, 25), "1w", None, today=date(2026, 10, 21)) == date(2026, 11, 1)


def test_overdue_series_catches_up_instead_of_spawning_an_overdue_task():
    # Due weekly on Mondays since 1 Sep; completed on 21 Oct. The next one must not be in the past.
    result = next_due_date(date(2026, 9, 1), "1w", None, today=date(2026, 10, 21))

    assert result == date(2026, 10, 27) and result.weekday() == date(2026, 9, 1).weekday()


def test_a_task_due_today_repeats_into_the_future():
    assert next_due_date(date(2026, 10, 21), "1d", None, today=date(2026, 10, 21)) == date(2026, 10, 22)


def test_without_a_due_date_the_next_one_counts_from_today():
    assert next_due_date(None, "3d", None, today=date(2026, 10, 21)) == date(2026, 10, 24)


# --- lifecycle through the API -------------------------------------------------------------------


@pytest.fixture()
def today(monkeypatch):
    pinned = date(2026, 10, 21)
    monkeypatch.setattr(items_service, "_today", lambda: pinned)
    return pinned


def make(client, title="Water plants", **extra):
    payload = {"title": title, "type": "TODO", **extra}
    response = client.post("/api/items", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def all_items(client):
    return client.get("/api/items").json()


def test_recurrence_is_normalized_stored_and_returned(client):
    item = make(client, recurrence="Weekly", due_date="2026-10-21")

    assert item["recurrence"] == "1w"
    assert client.get(f"/api/items/{item['id']}").json()["recurrence"] == "1w"


def test_todos_without_a_rule_do_not_repeat(client):
    assert make(client)["recurrence"] is None


def test_invalid_rules_and_repeating_notes_are_rejected(client):
    assert client.post("/api/items", json={"title": "x", "type": "TODO", "recurrence": "sometimes"}).status_code == 422
    note = client.post("/api/items", json={"title": "x", "type": "NOTE", "recurrence": "1w"})
    assert note.status_code == 422 and "todos can repeat" in str(note.json())


def test_completing_a_repeating_todo_creates_the_next_one(client, today):
    original = make(client, content="Use the green can", priority="HIGH", tags=["home"],
                    due_date="2026-10-21", recurrence="1w")

    done = client.post(f"/api/items/{original['id']}/complete").json()
    items = all_items(client)
    nxt = next(i for i in items if i["id"] != original["id"])

    assert done["completed"] is True
    assert len(items) == 2
    assert (nxt["title"], nxt["content"], nxt["priority"], nxt["tags"], nxt["recurrence"]) == (
        "Water plants", "Use the green can", "HIGH", ["home"], "1w")
    assert nxt["completed"] is False and nxt["due_date"] == "2026-10-28" and nxt["type"] == "TODO"


def test_completing_through_patch_also_spawns_the_next_one(client, today):
    original = make(client, due_date="2026-10-21", recurrence="1d")

    client.patch(f"/api/items/{original['id']}", json={"completed": True})

    assert sorted(i["due_date"] for i in all_items(client)) == ["2026-10-21", "2026-10-22"]


def test_non_repeating_todos_do_not_spawn_anything(client, today):
    item = make(client, due_date="2026-10-21")

    client.post(f"/api/items/{item['id']}/complete")

    assert len(all_items(client)) == 1


def test_reopening_and_recompleting_does_not_create_duplicates(client, today):
    item = make(client, due_date="2026-10-21", recurrence="1w")

    client.post(f"/api/items/{item['id']}/complete")
    client.post(f"/api/items/{item['id']}/reopen")
    client.post(f"/api/items/{item['id']}/complete")

    assert len(all_items(client)) == 2


def test_completing_an_already_completed_item_again_does_nothing(client, today):
    item = make(client, due_date="2026-10-21", recurrence="1w")

    client.post(f"/api/items/{item['id']}/complete")
    client.post(f"/api/items/{item['id']}/complete")
    client.patch(f"/api/items/{item['id']}", json={"completed": True})

    assert len(all_items(client)) == 2


def test_a_long_overdue_series_does_not_spawn_an_overdue_task(client, today):
    item = make(client, due_date="2026-09-01", recurrence="1w")

    client.post(f"/api/items/{item['id']}/complete")

    spawned = next(i for i in all_items(client) if i["id"] != item["id"])
    assert spawned["due_date"] == "2026-10-27"


def test_month_end_series_keeps_its_anchor_across_completions(client, today, monkeypatch):
    item = make(client, due_date="2026-01-31", recurrence="1m")
    seen = []
    current_id = item["id"]
    for pinned in (date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31)):
        monkeypatch.setattr(items_service, "_today", lambda p=pinned: p)
        client.post(f"/api/items/{current_id}/complete")
        nxt = max(all_items(client), key=lambda i: i["id"])
        seen.append(nxt["due_date"])
        current_id = nxt["id"]

    assert seen == ["2026-02-28", "2026-03-31", "2026-04-30"]


def test_repeating_without_a_due_date_starts_from_today(client, today):
    item = make(client, recurrence="3d")

    client.post(f"/api/items/{item['id']}/complete")

    assert max(all_items(client), key=lambda i: i["id"])["due_date"] == "2026-10-24"


def test_weekday_rule_skips_weekends(client, today):
    item = make(client, due_date="2026-10-23", recurrence="weekdays")  # a Friday

    client.post(f"/api/items/{item['id']}/complete")

    assert max(all_items(client), key=lambda i: i["id"])["due_date"] == "2026-10-26"


def test_changing_or_clearing_the_rule(client, today):
    item = make(client, due_date="2026-10-21", recurrence="1w")

    changed = client.patch(f"/api/items/{item['id']}", json={"recurrence": "2w"}).json()
    cleared = client.patch(f"/api/items/{item['id']}", json={"recurrence": None}).json()
    untouched = client.patch(f"/api/items/{item['id']}", json={"title": "Renamed"}).json()

    assert changed["recurrence"] == "2w"
    assert cleared["recurrence"] is None
    assert untouched["recurrence"] is None
    client.post(f"/api/items/{item['id']}/complete")
    assert len(all_items(client)) == 1  # no longer repeats


def test_rule_survives_unrelated_edits(client):
    item = make(client, due_date="2026-10-21", recurrence="1w")

    updated = client.patch(f"/api/items/{item['id']}", json={"title": "New title", "priority": "LOW"}).json()

    assert updated["recurrence"] == "1w"


def test_moving_the_due_date_re_anchors_a_monthly_series(client, today, monkeypatch):
    item = make(client, due_date="2026-01-31", recurrence="1m")
    client.patch(f"/api/items/{item['id']}", json={"due_date": "2026-01-15"})
    monkeypatch.setattr(items_service, "_today", lambda: date(2026, 1, 15))

    client.post(f"/api/items/{item['id']}/complete")

    assert max(all_items(client), key=lambda i: i["id"])["due_date"] == "2026-02-15"


def test_converting_to_a_note_clears_the_rule_and_back_to_todo_does_not_restore_it(client):
    item = make(client, due_date="2026-10-21", recurrence="1w")

    note = client.post(f"/api/items/{item['id']}/convert").json()
    todo = client.post(f"/api/items/{item['id']}/convert").json()

    assert note["type"] == "NOTE" and note["recurrence"] is None
    assert todo["type"] == "TODO" and todo["recurrence"] is None


def test_setting_a_rule_on_a_note_is_a_422(client):
    note = client.post("/api/items", json={"title": "n", "type": "NOTE"}).json()

    response = client.patch(f"/api/items/{note['id']}", json={"recurrence": "1w"})

    assert response.status_code == 422
    assert client.get(f"/api/items/{note['id']}").json()["recurrence"] is None


def test_turning_a_todo_into_a_note_and_setting_a_rule_in_one_patch_is_rejected_cleanly(client):
    item = make(client, due_date="2026-10-21")

    response = client.patch(f"/api/items/{item['id']}", json={"type": "NOTE", "recurrence": "1w"})

    assert response.status_code == 422
    assert client.get(f"/api/items/{item['id']}").json()["type"] == "TODO"  # nothing half-applied


def test_spawned_items_share_tags_without_duplicating_them(client, today):
    item = make(client, due_date="2026-10-21", recurrence="1d", tags=["a", "b"])

    client.post(f"/api/items/{item['id']}/complete")

    assert client.get("/api/tags").json() == [{"name": "a", "count": 2}, {"name": "b", "count": 2}]


# --- Quick Add -----------------------------------------------------------------------------------

WED = date(2026, 10, 21)


@pytest.mark.parametrize(
    ("text", "title", "rule", "due"),
    [
        ("water plants every 3 days", "water plants", "3d", date(2026, 10, 21)),
        ("pay rent every month", "pay rent", "1m", date(2026, 10, 21)),
        ("review budget every year", "review budget", "1y", date(2026, 10, 21)),
        ("gym every other week", "gym", "2w", date(2026, 10, 21)),
        ("standup every weekday", "standup", "weekdays", date(2026, 10, 21)),
        ("standup every monday", "standup", "1w", date(2026, 10, 26)),
        ("standup every wednesday", "standup", "1w", date(2026, 10, 21)),  # today is a Wednesday
        ("call mom weekly", "call mom", "1w", date(2026, 10, 21)),
        ("trash daily tomorrow", "trash", "1d", date(2026, 10, 22)),
        ("review every year dec 1", "review", "1y", date(2026, 12, 1)),
        ("email me weekly #work !low", "email me", "1w", date(2026, 10, 21)),
    ],
)
def test_quick_add_repeat_phrases(text, title, rule, due):
    r = parse_quick_add(text, today=WED)
    assert (r.title, r.recurrence, r.due_date) == (title, rule, due)


@pytest.mark.parametrize(
    "text",
    ["weekly report", "monthly budget review", "daily standup notes", "every 2 weeks", "yearly"],
)
def test_quick_add_leaves_ordinary_titles_and_notes_alone(text):
    r = parse_quick_add(text, today=WED)
    assert r.recurrence is None and r.title == text


def test_quick_add_notes_never_repeat_and_keep_the_words():
    r = parse_quick_add("note: gym every week", today=WED)

    assert (r.item_type.value, r.recurrence, r.title) == ("NOTE", None, "gym every week")


def test_quick_add_explicit_date_wins_over_the_weekday_anchor():
    r = parse_quick_add("standup every monday dec 7", today=WED)
    assert (r.recurrence, r.due_date) == ("1w", date(2026, 12, 7))


def test_parse_endpoint_returns_the_rule(client):
    body = client.post("/api/items/parse", json={"text": "water plants every 2 weeks"}).json()

    assert body["title"] == "water plants" and body["recurrence"] == "2w" and body["due_date"] is not None


# --- export / import -----------------------------------------------------------------------------


def test_json_export_and_import_round_trip_keeps_rules_and_anchors(client):
    make(client, "Rent", due_date="2026-01-31", recurrence="1m")
    export = client.get("/api/backup/export.json").json()
    assert export["items"][0]["recurrence"] == "1m" and export["items"][0]["recurrence_day"] == 31
    for item in all_items(client):
        client.delete(f"/api/items/{item['id']}")

    client.post("/api/backup/import?mode=merge", json=export)

    restored = all_items(client)[0]
    assert restored["recurrence"] == "1m"


def test_unreadable_rules_in_an_import_are_dropped_not_fatal(client):
    payload = {"format": "taskflow-export", "version": 1, "items": [
        {"title": "Good", "type": "TODO", "recurrence": "2w"},
        {"title": "Odd", "type": "TODO", "recurrence": "whenever"},
        {"title": "Note", "type": "NOTE", "recurrence": "1w"},
    ]}

    result = client.post("/api/backup/import?mode=merge", json=payload)
    got = {i["title"]: i["recurrence"] for i in all_items(client)}

    assert result.status_code == 200
    assert got == {"Good": "2w", "Odd": None, "Note": None}


def test_markdown_export_and_import_keep_the_repeat_rule(client):
    import io
    import zipfile

    make(client, "Water plants", due_date="2026-10-21", recurrence="2w")
    archive = client.get("/api/backup/export.zip").content
    assert "repeat: 2w" in zipfile.ZipFile(io.BytesIO(archive)).read("Todos/Water plants.md").decode()
    for item in all_items(client):
        client.delete(f"/api/items/{item['id']}")

    client.post("/api/backup/import?mode=merge", content=archive)

    assert all_items(client)[0]["recurrence"] == "2w"
