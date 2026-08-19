import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from database import WAKE, ARRIVE_WORK, LEAVE_WORK, SLEEP
from message_parser import categorize, parse_backfill


@pytest.mark.parametrize("text,expected", [
    ("Goodmorning", WAKE),
    ("goodmorning", WAKE),
    ("  Awake  ", WAKE),
    ("I'm awake", WAKE),
    ("im awake", WAKE),
    ("At work", ARRIVE_WORK),
    ("Arrived at work", ARRIVE_WORK),
    ("arrived", ARRIVE_WORK),
    ("Leaving", LEAVE_WORK),
    ("Left", LEAVE_WORK),
    ("Leaving work", LEAVE_WORK),
    ("Left work", LEAVE_WORK),
    ("Goodbye", LEAVE_WORK),
    ("Bye work", LEAVE_WORK),
    ("Goodnight", SLEEP),
    ("Bedtime", SLEEP),
    ("Going to sleep", SLEEP),
    ("Sleeping", SLEEP),
    ("GOODNIGHT!", SLEEP),
])
def test_categorize_recognized_phrases(text, expected):
    assert categorize(text) == expected


@pytest.mark.parametrize("text", [
    "hello",
    "what's for dinner",
    "",
    "leftovers",  # contains "left" as a substring but isn't the phrase "left"
])
def test_categorize_unrecognized_returns_none(text):
    assert categorize(text) is None


# Fixed reference "now" so relative day words resolve to known dates.
_NOW = datetime(2026, 8, 19, 14, 0)  # Wednesday, Aug 19 2026


@pytest.mark.parametrize("text,expected_category,expected_dt", [
    ("I arrived to work at 9:00 AM yesterday", ARRIVE_WORK, datetime(2026, 8, 18, 9, 0)),
    ("I went to sleep at 11:00 PM last night", SLEEP, datetime(2026, 8, 18, 23, 0)),
    ("I got to work at 8:30 AM this morning", ARRIVE_WORK, datetime(2026, 8, 19, 8, 30)),
    ("woke up at 6:45am today", WAKE, datetime(2026, 8, 19, 6, 45)),
    ("left work at 5pm yesterday", LEAVE_WORK, datetime(2026, 8, 18, 17, 0)),
    ("went to bed at 10:15 p.m.", SLEEP, datetime(2026, 8, 19, 22, 15)),  # no day word -> today
    ("12:00 AM sleeping last night", SLEEP, datetime(2026, 8, 18, 0, 0)),
])
def test_parse_backfill_recognized(text, expected_category, expected_dt):
    result = parse_backfill(text, _NOW)
    assert result == (expected_category, expected_dt)


@pytest.mark.parametrize("text", [
    "I arrived to work",  # no time at all
    "at 9:00 AM yesterday",  # time present but no category keyword
    "I ate leftovers at 9pm yesterday",  # "left" shouldn't match inside "leftovers"
    "",
    "hello there",
])
def test_parse_backfill_unrecognized_returns_none(text):
    assert parse_backfill(text, _NOW) is None


def test_parse_backfill_rejects_invalid_hour():
    assert parse_backfill("arrived at work at 13:00 pm yesterday", _NOW) is None
