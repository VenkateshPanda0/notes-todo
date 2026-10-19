from datetime import date

import pytest

from backend.app.models.item import ItemType, Priority
from backend.app.services.quick_add import parse_quick_add

# A Wednesday, so weekday maths is easy to follow.
TODAY = date(2026, 10, 14)


def parse(text: str):
    return parse_quick_add(text, today=TODAY)


def test_plain_text_is_a_medium_priority_todo_with_no_date():
    r = parse("buy milk")
    assert (r.title, r.item_type, r.priority, r.due_date) == (
        "buy milk", ItemType.TODO, Priority.MEDIUM, None,
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("call dentist today", date(2026, 10, 14)),
        ("call dentist tomorrow", date(2026, 10, 15)),
        ("call dentist tmr", date(2026, 10, 15)),
        ("call dentist on friday", date(2026, 10, 16)),
        ("call dentist next friday", date(2026, 10, 16)),
        ("call dentist by Monday", date(2026, 10, 19)),
        ("call dentist wednesday", date(2026, 10, 21)),  # same weekday -> a week out, never today
        ("call dentist next week", date(2026, 10, 19)),  # Monday of next week
        ("call dentist in 3 days", date(2026, 10, 17)),
        ("call dentist in 2 weeks", date(2026, 10, 28)),
        ("call dentist 2026-12-25", date(2026, 12, 25)),
        ("call dentist dec 25", date(2026, 12, 25)),
        ("call dentist 25th of december", date(2026, 12, 25)),
        ("call dentist jan 5", date(2027, 1, 5)),  # already passed this year -> next year
        ("call dentist oct 14", date(2026, 10, 14)),  # today is not "passed"
    ],
)
def test_date_phrases(text, expected):
    r = parse(text)
    assert r.due_date == expected
    assert r.title == "call dentist"


@pytest.mark.parametrize(
    ("text", "expected"),
    [("!high", Priority.HIGH), ("!h", Priority.HIGH), ("!med", Priority.MEDIUM),
     ("!low", Priority.LOW), ("!LOW", Priority.LOW)],
)
def test_priority_markers(text, expected):
    r = parse(f"write report {text}")
    assert r.priority == expected
    assert r.title == "write report"


def test_everything_combined():
    r = parse("call dentist next friday !high")
    assert (r.title, r.priority, r.due_date) == ("call dentist", Priority.HIGH, date(2026, 10, 16))


def test_note_prefix_makes_a_note_and_keeps_date_words():
    r = parse("note: meeting tomorrow went well")
    assert r.item_type == ItemType.NOTE
    assert r.title == "meeting tomorrow went well"
    assert r.due_date is None


def test_todo_prefix_is_accepted():
    r = parse("todo: file taxes tomorrow")
    assert r.item_type == ItemType.TODO
    assert r.title == "file taxes"


@pytest.mark.parametrize("text", ["I sat on the chair", "sun is out", "may the force", "wed shoes", "50% off!"])
def test_ordinary_words_are_not_mistaken_for_dates_or_priority(text):
    r = parse(text)
    assert r.title == text
    assert r.due_date is None
    assert r.priority == Priority.MEDIUM


def test_invalid_calendar_dates_stay_in_the_title():
    r = parse("party feb 30")
    assert r.due_date is None
    assert r.title == "party feb 30"


def test_only_keywords_keeps_the_original_text_as_the_title():
    r = parse("tomorrow")
    assert r.title == "tomorrow"
    assert r.due_date is None


def test_extra_whitespace_and_punctuation_are_cleaned_up():
    assert parse("  call   dentist ,  tomorrow  ").title == "call dentist"


def test_title_is_capped_at_the_column_length():
    assert len(parse("x" * 400).title) == 255


def test_parse_endpoint_previews_without_saving(client):
    response = client.post("/api/items/parse", json={"text": "call dentist tomorrow !high"})
    body = response.json()

    assert response.status_code == 200
    assert body["title"] == "call dentist"
    assert body["type"] == "TODO"
    assert body["priority"] == "HIGH"
    assert body["due_date"] is not None
    assert client.get("/api/items").json() == []


def test_parse_endpoint_requires_the_session_when_locked(client):
    client.post("/api/auth/setup", json={"password": "secret1"})

    assert client.post("/api/items/parse", json={"text": "x"}).status_code == 401


def test_parse_endpoint_rejects_empty_text(client):
    assert client.post("/api/items/parse", json={"text": ""}).status_code == 422
