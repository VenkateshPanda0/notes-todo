"""Parse a single line of quick-capture text into item fields.

Examples:
    "call dentist tomorrow !high"  -> TODO, due tomorrow, HIGH priority
    "note: wifi password is ..."   -> NOTE
    "plan trip #travel #2026"      -> tag "travel" ("#2026" is left in the title: tags start with a letter)
    "water plants every 3 days"    -> repeats every 3 days (also: every week/month/year, every other
                                      week, every weekday, every monday, daily/weekly/monthly/yearly
                                      at the END of the text)

The grammar is deliberately small and predictable. Anything not recognized stays in the title.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from ..models.item import ItemType, Priority
from .recurrence import normalize_recurrence
from .tags import MAX_TAG_LENGTH, MAX_TAGS_PER_ITEM

_WEEKDAYS = {
    # Short forms that are also common words (mon, wed, sat, sun) are intentionally omitted.
    "monday": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5,
    "sunday": 6,
}

_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

_PRIORITIES = {
    "high": Priority.HIGH, "h": Priority.HIGH,
    "medium": Priority.MEDIUM, "med": Priority.MEDIUM, "m": Priority.MEDIUM,
    "low": Priority.LOW, "l": Priority.LOW,
}

_PREFIX = r"(?:\b(?:on|by|due|before)\s+)?"
_WEEKDAY_RE = "|".join(sorted(_WEEKDAYS, key=len, reverse=True))
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))


@dataclass(frozen=True)
class QuickAddResult:
    title: str
    item_type: ItemType
    priority: Priority
    due_date: date | None
    tags: tuple[str, ...] = ()
    recurrence: str | None = None


_UNIT_CODE = {"day": "d", "week": "w", "month": "m", "year": "y"}
_EVERY_N = re.compile(r"\bevery\s+(\d{1,3})\s+(day|week|month|year)s?\b", re.IGNORECASE)
_EVERY_OTHER = re.compile(r"\bevery\s+other\s+(day|week|month|year)\b", re.IGNORECASE)
_EVERY_UNIT = re.compile(r"\bevery\s+(day|week|month|year)\b", re.IGNORECASE)
_EVERY_WEEKDAYS = re.compile(r"\bevery\s+weekday\b", re.IGNORECASE)
_EVERY_NAMED_DAY = re.compile(rf"\bevery\s+({_WEEKDAY_RE})\b", re.IGNORECASE)
# Bare adverbs are only read as a repeat at the very end ("call mom weekly"), so titles such as
# "weekly report" or "monthly budget review" are left alone.
_TRAILING_ADVERB = re.compile(r"\b(daily|weekly|monthly|yearly|annually|weekdays)\s*$", re.IGNORECASE)


def _extract_recurrence(text: str) -> tuple[str | None, int | None, str]:
    """Find an explicit "every ..." phrase. Returns (rule, weekday_anchor, text_without_it)."""
    if m := _EVERY_N.search(text):
        rule = f"{int(m[1])}{_UNIT_CODE[m[2].lower()]}"
        return normalize_recurrence(rule), None, text[: m.start()] + " " + text[m.end():]
    if m := _EVERY_OTHER.search(text):
        return f"2{_UNIT_CODE[m[1].lower()]}", None, text[: m.start()] + " " + text[m.end():]
    if m := _EVERY_WEEKDAYS.search(text):
        return "weekdays", None, text[: m.start()] + " " + text[m.end():]
    if m := _EVERY_NAMED_DAY.search(text):
        return "1w", _WEEKDAYS[m[1].lower()], text[: m.start()] + " " + text[m.end():]
    if m := _EVERY_UNIT.search(text):
        return f"1{_UNIT_CODE[m[1].lower()]}", None, text[: m.start()] + " " + text[m.end():]
    return None, None, text


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _next_weekday(today: date, weekday: int) -> date:
    """The next occurrence of a weekday, never today itself."""
    return today + timedelta(days=(weekday - today.weekday()) % 7 or 7)


def _month_day(today: date, month: int, day: int) -> date | None:
    """A month/day this year, rolled to next year if it has already passed."""
    candidate = _safe_date(today.year, month, day)
    if candidate is None:
        return None
    if candidate < today:
        return _safe_date(today.year + 1, month, day)
    return candidate


def _find_date(text: str, today: date) -> tuple[date, re.Match[str]] | None:
    """Find the first recognizable date phrase. Returns the date and the span to remove."""
    flags = re.IGNORECASE

    if m := re.search(rf"{_PREFIX}\b(\d{{4}})-(\d{{2}})-(\d{{2}})\b", text, flags):
        d = _safe_date(int(m[1]), int(m[2]), int(m[3]))
        if d:
            return d, m

    if m := re.search(rf"{_PREFIX}\b(today|tonight)\b", text, flags):
        return today, m

    if m := re.search(rf"{_PREFIX}\b(tomorrow|tmrw|tmr)\b", text, flags):
        return today + timedelta(days=1), m

    if m := re.search(rf"{_PREFIX}\bnext\s+week\b", text, flags):
        return today + timedelta(days=7 - today.weekday()), m

    if m := re.search(rf"{_PREFIX}\bin\s+(\d{{1,3}})\s+(day|days|week|weeks)\b", text, flags):
        n = int(m[1]) * (7 if m[2].lower().startswith("week") else 1)
        return today + timedelta(days=n), m

    if m := re.search(rf"{_PREFIX}\b(?:next\s+)?({_WEEKDAY_RE})\b", text, flags):
        return _next_weekday(today, _WEEKDAYS[m[1].lower()]), m

    # "jan 5", "january 5th"
    if m := re.search(rf"{_PREFIX}\b({_MONTH_RE})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", text, flags):
        d = _month_day(today, _MONTHS[m[1].lower()], int(m[2]))
        if d:
            return d, m

    # "5 jan", "5th of january"
    if m := re.search(rf"{_PREFIX}\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({_MONTH_RE})\b", text, flags):
        d = _month_day(today, _MONTHS[m[2].lower()], int(m[1]))
        if d:
            return d, m

    return None


def parse_quick_add(text: str, today: date | None = None) -> QuickAddResult:
    """Turn free text into a title plus optional type, priority and due date."""
    today = today or date.today()
    original = text.strip()
    working = original

    item_type = ItemType.TODO
    if m := re.match(r"^\s*(note|todo)\s*:\s*", working, re.IGNORECASE):
        item_type = ItemType.NOTE if m[1].lower() == "note" else ItemType.TODO
        working = working[m.end():]

    priority = Priority.MEDIUM
    if m := re.search(r"(?<!\S)!(high|medium|med|low|h|m|l)\b", working, re.IGNORECASE):
        priority = _PRIORITIES[m[1].lower()]
        working = working[: m.start()] + " " + working[m.end():]

    tags: list[str] = []
    for m in list(re.finditer(rf"(?<!\S)#([^\W\d_][\w-]{{0,{MAX_TAG_LENGTH - 1}}})(?![\w-])", working)):
        name = m[1].lower()
        if name not in tags and len(tags) < MAX_TAGS_PER_ITEM:
            tags.append(name)
    working = re.sub(
        rf"(?<!\S)#[^\W\d_][\w-]{{0,{MAX_TAG_LENGTH - 1}}}(?![\w-])", " ", working
    )

    recurrence: str | None = None
    weekday_anchor: int | None = None
    if item_type == ItemType.TODO:
        recurrence, weekday_anchor, working = _extract_recurrence(working)

    due_date: date | None = None
    # Notes have no due date, so leave date words in their title.
    if item_type == ItemType.TODO and (found := _find_date(working, today)):
        due_date, m = found
        working = working[: m.start()] + " " + working[m.end():]

    if item_type == ItemType.TODO and recurrence is None:
        if m := _TRAILING_ADVERB.search(working):
            recurrence = normalize_recurrence(m[1])
            working = working[: m.start()]

    if recurrence and due_date is None:
        # A repeating task needs a first date: "every monday" starts on the next Monday (today if it
        # is Monday); everything else starts today.
        due_date = (
            today + timedelta(days=(weekday_anchor - today.weekday()) % 7)
            if weekday_anchor is not None
            else today
        )

    title = re.sub(r"\s+", " ", working).strip(" ,;-")
    if not title:
        # Everything was a keyword (e.g. just "tomorrow"): keep the original text as the title.
        title = original
        due_date = None
        priority = Priority.MEDIUM
        tags = []
        recurrence = None
    return QuickAddResult(
        title=title[:255],
        item_type=item_type,
        priority=priority,
        due_date=due_date,
        tags=tuple(tags),
        recurrence=recurrence,
    )
