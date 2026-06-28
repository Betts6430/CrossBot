"""Candidate scoring / ranking.

Combines signals into a single confidence score per candidate, e.g. clue-match
strength (database), word-list quality weight, and agreement with already-fixed
crossing letters. Used by candidates.py and csp.py. Not implemented yet.
"""

from __future__ import annotations


def score_candidate(*args: object, **kwargs: object) -> float:
    """Return a 0..1 confidence for a candidate answer."""
    raise NotImplementedError
