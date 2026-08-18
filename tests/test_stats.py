import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Event, WAKE, SLEEP
from stats import build_days_table, category_stats, all_category_stats, RANGE_DAYS


def _add_event(db, category, dt, raw="test"):
    event = Event(category=category, timestamp=dt, raw_message=raw)
    db.add(event)
    db.commit()
    return event


def test_build_days_table_uses_earliest_event_per_day(db_session):
    day = date(2026, 8, 1)
    _add_event(db_session, WAKE, datetime(2026, 8, 1, 7, 30))
    _add_event(db_session, WAKE, datetime(2026, 8, 1, 7, 45))  # duplicate same day, later

    by_date = build_days_table(db_session)

    assert by_date[day][WAKE] == datetime(2026, 8, 1, 7, 30)


def test_category_stats_avg_min_max(db_session):
    _add_event(db_session, WAKE, datetime(2026, 8, 1, 7, 0))
    _add_event(db_session, WAKE, datetime(2026, 8, 2, 8, 0))
    _add_event(db_session, WAKE, datetime(2026, 8, 3, 6, 0))

    by_date = build_days_table(db_session)
    stats = category_stats(by_date, WAKE)

    assert stats["count"] == 3
    assert stats["earliest"] == "06:00"
    assert stats["latest"] == "08:00"
    assert stats["average"] == "07:00"


def test_category_stats_none_when_no_data(db_session):
    by_date = build_days_table(db_session)
    assert category_stats(by_date, SLEEP) is None


def test_category_stats_since_filters_out_old_days(db_session):
    _add_event(db_session, WAKE, datetime(2020, 1, 1, 5, 0))  # far in the past
    _add_event(db_session, WAKE, datetime(2026, 8, 1, 9, 0))

    by_date = build_days_table(db_session)
    stats = category_stats(by_date, WAKE, since=date(2026, 1, 1))

    assert stats["count"] == 1
    assert stats["average"] == "09:00"


def test_all_category_stats_returns_every_category(db_session):
    _add_event(db_session, WAKE, datetime(2026, 8, 1, 7, 0))
    by_date = build_days_table(db_session)

    stats = all_category_stats(by_date, "week", today=date(2026, 8, 1))

    assert set(stats.keys()) == {"wake", "arrive_work", "leave_work", "sleep"}
    assert stats["wake"]["count"] == 1
    assert stats["sleep"] is None


def test_range_days_ordering():
    assert RANGE_DAYS["week"] < RANGE_DAYS["month"] < RANGE_DAYS["quarter"] < RANGE_DAYS["year"]


def test_sleep_stats_handle_midnight_wraparound(db_session):
    # Bedtimes of 11:30 PM and 12:30 AM should average to ~midnight, not noon.
    _add_event(db_session, SLEEP, datetime(2026, 8, 1, 23, 30))
    _add_event(db_session, SLEEP, datetime(2026, 8, 2, 0, 30))

    by_date = build_days_table(db_session)
    stats = category_stats(by_date, SLEEP)

    assert stats["average"] == "00:00"
    assert stats["earliest"] == "23:30"
    assert stats["latest"] == "00:30"
