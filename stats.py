"""
Aggregation of logged Events into per-day, per-category data points and
avg/min/max stats over a date range.

If the same category gets logged more than once on the same day (e.g. the
user accidentally sends "awake" twice), the EARLIEST timestamp that day is
treated as the day's data point for that category. This keeps a duplicate/
correction message from skewing the average.
"""

from collections import defaultdict
from datetime import date, timedelta

from database import Event, CATEGORIES, SLEEP

# Categories whose times can fall past midnight (e.g. bedtime at 12:30 AM).
# Averaging clock times naively wraps around noon (avg of 23:30 and 00:30
# would come out as 12:00, which is nonsense for a bedtime) - so for these
# categories, any time before noon is treated as "really" belonging to the
# previous evening for the purposes of min/avg/max, then shifted back into
# a normal 00:00-23:59 display value.
WRAP_MIDNIGHT_CATEGORIES = {SLEEP}
_NOON = 12 * 60
_DAY = 24 * 60

RANGE_WEEK = "week"
RANGE_MONTH = "month"
RANGE_QUARTER = "quarter"
RANGE_YEAR = "year"

RANGE_DAYS = {
    RANGE_WEEK: 7,
    RANGE_MONTH: 30,
    RANGE_QUARTER: 90,
    RANGE_YEAR: 365,
}


def build_days_table(db) -> dict:
    """Return {date: {category: datetime}} - one earliest timestamp per
    category per day, across all logged events."""
    events = db.query(Event).order_by(Event.timestamp.asc()).all()
    by_date = defaultdict(dict)
    for event in events:
        day = event.timestamp.date()
        existing = by_date[day].get(event.category)
        if existing is None or event.timestamp < existing:
            by_date[day][event.category] = event.timestamp
    return dict(by_date)


def time_of_day_minutes(dt) -> int:
    return dt.hour * 60 + dt.minute


def _format_minutes(minutes: float) -> str:
    total = int(round(minutes)) % (24 * 60)
    hours, mins = divmod(total, 60)
    return f"{hours:02d}:{mins:02d}"


def category_stats(by_date: dict, category: str, since: date | None = None) -> dict | None:
    """avg/min/max/count for one category, optionally restricted to days >= since."""
    minutes = []
    for day, categories in by_date.items():
        if category not in categories:
            continue
        if since and day < since:
            continue
        minutes.append(time_of_day_minutes(categories[category]))

    if not minutes:
        return None

    if category in WRAP_MIDNIGHT_CATEGORIES:
        minutes = [m + _DAY if m < _NOON else m for m in minutes]

    return {
        "count": len(minutes),
        "average": _format_minutes(sum(minutes) / len(minutes)),
        "earliest": _format_minutes(min(minutes)),
        "latest": _format_minutes(max(minutes)),
    }


def all_category_stats(by_date: dict, range_name: str, today: date | None = None) -> dict:
    """{category: stats-or-None} for every category, over the named range."""
    today = today or date.today()
    since = today - timedelta(days=RANGE_DAYS[range_name] - 1)
    return {category: category_stats(by_date, category, since=since) for category in CATEGORIES}
