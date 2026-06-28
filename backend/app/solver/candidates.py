"""Per-slot candidate generation.

For each slot, produce a ranked list of possible answers from:
  - the clue-answer database (exact + fuzzy clue match), and
  - the scored word list (length-filtered), for novel clues.

Candidates feed the CSP solver in csp.py. Not implemented yet.
"""

from __future__ import annotations

from app.models import Puzzle


def generate(puzzle: Puzzle) -> dict[str, list[tuple[str, float]]]:
    """Map each slot id -> list of (answer, score) candidates."""
    raise NotImplementedError
