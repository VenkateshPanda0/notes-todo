"""Recurring todos: rule parsing and next-date calculation.

A rule is stored as a short canonical string:
    "3d"  every 3 days        "1w"  every week      "2m"  every 2 months
    "1y"  every year          "weekdays"  Monday to Friday

Months and years keep an "anchor" day (the day of the month the series started on) so a monthly
task due on the 31st goes Jan 31 -> Feb 28 -> Mar 31 instead of drifting to the 28th for good.
"""

import calendar
import re
from datetime import date, timedelta

_RULE = re.compile(r"^(?:(\d{1,3})([dwmy])|weekdays)$")
_ALIASES = {
    "daily": "1d",
    "weekly": "1w",
    "monthly": "1m",
    "yearly": "1y",
    "annually": "1y",
    "every weekday": "weekdays",
}
_UNIT_DAYS = {"d": 1, "w": 7}
_NAMES = {"d": "day", "w": "week", "m": "month", "y": "year"}


def normalize_recurrence(value: str | None) -> str | None:
    """Canonicalize a rule ("Weekly" -> "1w"). Returns None for no repeat; raises ValueError if invalid."""
    if value is None:
        return None
    text = value.strip().lower()
    if text in ("", "none", "never", "no"):
        return None
    text = _ALIASES.get(text, text)
    match = _RULE.match(text)
    if not match:
        raise ValueError(
            f"Invalid repeat rule {value!r}: use daily, weekdays, weekly, monthly, yearly, or a number "
            "and unit such as 2w (every 2 weeks)."
        )
    if text == "weekdays":
        return text
    count = int(match.group(1))
    if count < 1:
        raise ValueError("A repeat interval must be at least 1.")
    return f"{count}{match.group(2)}"


def describe_recurrence(rule: str | None) -> str:
    """Human text for a canonical rule, e.g. "2w" -> "Every 2 weeks"."""
    if not rule:
        return "Does not repeat"
    if rule == "weekdays":
        return "Every weekday"
    count, unit = int(rule[:-1]), rule[-1]
    if count == 1:
        return {"d": "Daily", "w": "Weekly", "m": "Monthly", "y": "Yearly"}[unit]
    return f"Every {count} {_NAMES[unit]}s"


def _add_months(start: date, months: int, anchor_day: int | None) -> date:
    index = start.month - 1 + months
    year, month = start.year + index // 12, index % 12 + 1
    day = min(anchor_day or start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def advance(current: date, rule: str, anchor_day: int | None = None) -> date:
    """The single next occurrence after `current`."""
    if rule == "weekdays":
        following = current + timedelta(days=1)
        while following.weekday() >= 5:  # skip Saturday and Sunday
            following += timedelta(days=1)
        return following
    count, unit = int(rule[:-1]), rule[-1]
    if unit in _UNIT_DAYS:
        return current + timedelta(days=count * _UNIT_DAYS[unit])
    if unit == "m":
        return _add_months(current, count, anchor_day)
    return _add_months(current, count * 12, anchor_day)


def next_due_date(due: date | None, rule: str, anchor_day: int | None, today: date) -> date:
    """The due date for the next occurrence once the current one is completed.

    Counts from the current due date (or today if it has none). If that lands in the past, which
    happens when a task was completed long after it was due, it keeps stepping forward so the
    new task is not born overdue.
    """
    following = advance(due or today, rule, anchor_day)
    for _ in range(2000):  # bounded: a daily rule is overdue by at most a few years of days
        if following >= today:
            break
        following = advance(following, rule, anchor_day)
    return following


def anchor_for(due: date | None, rule: str | None) -> int | None:
    """The anchor day to remember: only months/years need one."""
    if due and rule and rule[-1] in ("m", "y"):
        return due.day
    return None
