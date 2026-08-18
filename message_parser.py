"""
Free-text -> category classification for incoming Telegram messages.

Matching is deliberately exact (after normalizing case/punctuation/
whitespace) rather than fuzzy/substring - the phrase lists below were
specified by the user as the exact set of messages they intend to send.
Substring matching would risk misfiring on unrelated chat (e.g. "left"
inside some other sentence).
"""

import re
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
