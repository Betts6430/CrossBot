"""Candidate scoring helpers.

A candidate's score combines two signals, both in 0..1:
  - clue confidence (from the clue database) when the clue matches, and
  - a quality prior from how often the answer appears in real crosswords
    (clue-database answer frequency), which carries unclued fill and tie-breaks.
"""

from __future__ import annotations

import math

DEFAULT_SCORE = 50.0


def normalized(score: float) -> float:
    """Map a 0..100 word-list score to a 0..1 confidence."""
    return max(0.0, min(1.0, score / 100.0))


def quality_from_frequency(freq: int) -> float:
    """0..1 crossword-commonness prior from a clue-database answer count."""
    if freq <= 0:
        return 0.0
    return min(1.0, math.log1p(freq) / 12.0)  # ~0.33 @ 50, ~0.58 @ 1k, ~1 @ 160k
