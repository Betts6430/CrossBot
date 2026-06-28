"""Candidate scoring helpers.

For the engine MVP (word-list-only fill) scoring is simple: the word list's own
quality weight, normalized to 0..1 for the API's confidence field. When the
clue-answer database lands, clue-match strength gets folded in here.
"""

from __future__ import annotations

DEFAULT_SCORE = 50.0


def normalized(score: float) -> float:
    """Map a 0..100 word-list score to a 0..1 confidence."""
    return max(0.0, min(1.0, score / 100.0))
