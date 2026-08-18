import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from database import WAKE, ARRIVE_WORK, LEAVE_WORK, SLEEP
from message_parser import categorize


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
