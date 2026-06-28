"""Per-slot candidate generation.

For the engine MVP this is just word-list matching on the slot's current letter
pattern. This is the seam where the clue-answer database will add candidates:
the CSP solver only knows about `slot_candidates`, not where they come from.
"""

from __future__ import annotations

from app.solver.wordlist import WordList


def slot_candidates(wordlist: WordList, pattern: str) -> list[str]:
    """Ranked candidate fills for a slot given its pattern ('.' = unknown)."""
    return wordlist.match(pattern)
