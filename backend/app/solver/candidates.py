"""Candidate generation for the CSP solver.

The ``CandidateProvider`` is the one place that knows where fills come from, so
the solver stays agnostic. For a slot it offers, best-first:

  1. clue-conditioned answers from the clue database (if the slot has a clue),
     filtered to the slot's length and current letter pattern, then
  2. word-list matches for the pattern (the fill fallback).

``is_valid_fill`` accepts a completed entry if it's in the word list *or* the
clue database's answer vocabulary (crossword answers include proper nouns and
abbreviations the plain word list lacks).
"""

from __future__ import annotations

from app.data.clue_db import ClueDB
from app.solver.grid import Entry
from app.solver.scoring import DEFAULT_SCORE, normalized
from app.solver.wordlist import WordList


def _matches(pattern: str, word: str) -> bool:
    return all(p == "." or p == c for p, c in zip(pattern, word))


class CandidateProvider:
    def __init__(self, wordlist: WordList, clue_db: ClueDB | None = None) -> None:
        self.wordlist = wordlist
        self.clue_db = clue_db
        # clue text -> ranked (answer, score), cached for the duration of a solve.
        self._clue_cache: dict[str, list[tuple[str, float]]] = {}

    def _clue_lookup(self, clue: str) -> list[tuple[str, float]]:
        cached = self._clue_cache.get(clue)
        if cached is None:
            cached = self.clue_db.lookup(clue) if self.clue_db else []
            self._clue_cache[clue] = cached
        return cached

    def candidates(self, entry: Entry, pattern: str) -> list[str]:
        """Ranked candidate fills matching `pattern`, clue answers first."""
        length = len(pattern)
        out: list[str] = []
        seen: set[str] = set()

        if entry.clue and self.clue_db:
            for answer, _ in self._clue_lookup(entry.clue):
                if len(answer) == length and answer not in seen and _matches(pattern, answer):
                    seen.add(answer)
                    out.append(answer)

        for word in self.wordlist.match(pattern):
            if word not in seen:
                seen.add(word)
                out.append(word)

        return out

    def is_valid_fill(self, word: str) -> bool:
        if word in self.wordlist.scores:
            return True
        return self.clue_db.is_known_answer(word) if self.clue_db else False

    def confidence(self, entry: Entry, word: str) -> float:
        """0..1 confidence for a chosen answer (clue match beats word quality)."""
        if entry.clue and self.clue_db:
            for answer, score in self._clue_lookup(entry.clue):
                if answer == word:
                    return score
        return normalized(self.wordlist.scores.get(word, DEFAULT_SCORE))
