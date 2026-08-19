"""
Free-text -> category classification for incoming Telegram messages.

Matching is deliberately exact (after normalizing case/punctuation/
whitespace) rather than fuzzy/substring - the phrase lists below were
specified by the user as the exact set of messages they intend to send.
Substring matching would risk misfiring on unrelated chat (e.g. "left"
inside some other sentence).
"""

import re
from datetime import datetime, timedelta
from database import WAKE, ARRIVE_WORK, LEAVE_WORK, SLEEP

CATEGORY_PHRASES = {
    WAKE: [
        "goodmorning",
        "good morning",
        "awake",
        "im awake",
    ],
    ARRIVE_WORK: [
        "at work",
        "arrived at work",
        "arrived",
    ],
    LEAVE_WORK: [
        "leaving",
        "left",
        "leaving work",
        "left work",
        "goodbye",
        "bye work",
    ],
    SLEEP: [
        "goodnight",
        "good night",
        "bedtime",
        "going to sleep",
        "sleeping",
    ],
}

CATEGORY_LABELS = {
    WAKE: "\U0001F305 Wake up",
    ARRIVE_WORK: "\U0001F3E2 Arrived at work",
    LEAVE_WORK: "\U0001F6AA Left work",
    SLEEP: "\U0001F319 Bedtime",
}

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase, drop punctuation (incl. apostrophes), collapse whitespace."""
    text = text.lower().strip()
    text = _PUNCTUATION_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text


_NORMALIZED_LOOKUP = {
    normalize(phrase): category
    for category, phrases in CATEGORY_PHRASES.items()
    for phrase in phrases
}


def categorize(text: str) -> str | None:
    """Return one of WAKE/ARRIVE_WORK/LEAVE_WORK/SLEEP, or None if unrecognized."""
    return _NORMALIZED_LOOKUP.get(normalize(text))


# --- Backfilled entries, e.g. "I arrived to work at 9:00 AM yesterday" ---
#
# A backfilled entry can be phrased many different ways, so unlike the exact
# phrase list above this uses keyword/regex heuristics. It only fires when
# the message also contains an explicit clock time - a bare "I got to work"
# with no time has nothing to distinguish it from "log it now", so it's left
# to fall through to the instant-log path (and from there to "didn't
# understand" if it's not an exact phrase either).

_TIME_RE = re.compile(r"\b(\d{1,2})(?::([0-5]\d))?\s*([ap])\.?m\.?\b", re.IGNORECASE)
_YESTERDAY_RE = re.compile(r"\byesterday\b|\blast night\b", re.IGNORECASE)

# Word-boundary-anchored so e.g. "leftovers" doesn't match LEAVE_WORK's
# "left" the way it wouldn't match categorize()'s exact phrase list either.
_BACKFILL_CATEGORY_PATTERNS = {
    WAKE: re.compile(r"\bwoke\b|\bwake\w*|\bawake\b", re.IGNORECASE),
    ARRIVE_WORK: re.compile(r"\barriv\w*|\b(got|get|made it) (in )?to work\b|\bat work\b", re.IGNORECASE),
    LEAVE_WORK: re.compile(r"\bleav\w*|\bleft\b|\bgoodbye\b|\bbye\b", re.IGNORECASE),
    SLEEP: re.compile(r"\bsleep\w*|\bbed\w*", re.IGNORECASE),
}


def _extract_time(text: str) -> tuple[int, int] | None:
    """Return (hour24, minute) from the first clock time found, or None."""
    match = _TIME_RE.search(text)
    if not match:
        return None
    hour = int(match.group(1))
    if not (1 <= hour <= 12):
        return None
    minute = int(match.group(2) or 0)
    is_pm = match.group(3).lower() == "p"
    return (hour % 12) + (12 if is_pm else 0), minute


def _extract_day_offset(text: str) -> int:
    """Days to subtract from "now" - -1 for "yesterday"/"last night", else 0
    (covers "today"/"this morning"/"tonight" and no day reference at all)."""
    return -1 if _YESTERDAY_RE.search(text) else 0


def _categorize_backfill(text: str) -> str | None:
    matched = {category for category, pattern in _BACKFILL_CATEGORY_PATTERNS.items() if pattern.search(text)}
    return matched.pop() if len(matched) == 1 else None


def parse_backfill(text: str, reference_now: datetime) -> tuple[str, datetime] | None:
    """
    Try to interpret text as a backfilled log entry. Returns (category,
    timestamp) or None if it doesn't look like one - no explicit clock time,
    or no single unambiguous category keyword.
    """
    time_parts = _extract_time(text)
    if time_parts is None:
        return None

    category = _categorize_backfill(text)
    if category is None:
        return None

    hour, minute = time_parts
    target_date = (reference_now + timedelta(days=_extract_day_offset(text))).date()
    return category, datetime.combine(target_date, datetime.min.time()).replace(hour=hour, minute=minute)
