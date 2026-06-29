"""Candidate generation + scoring for the solver.

The ``CandidateProvider`` is the one place that knows where fills come from and
how good each is. For a slot and its current letter pattern it returns scored
candidates (best first):

  - score = max(clue confidence, quality prior), both in 0..1
  - clue confidence comes from the clue database when the slot has a clue and the
    word is a known answer for it; otherwise 0
  - the quality prior reflects how common the word is as a real crossword answer
    (clue-database frequency), so even unclued slots prefer real, common fills

``is_valid_fill`` accepts a completed entry if it's in the word list or the clue
database's answer vocabulary (crossword answers include proper nouns/abbrevs the
plain word list lacks).
"""

from __future__ import annotations

from app.data.clue_db import ClueDB
from app.solver.grid import Entry
from app.solver.scoring import DEFAULT_SCORE, normalized, quality_from_frequency
from app.solver.wordlist import WordList

# Quality contributes at most this on top of the floor, keeping it below a strong
# clue match (so clue answers win) but above an obscure fill.
_QUALITY_FLOOR = 0.05
_QUALITY_WEIGHT = 0.5
_WORDLIST_ONLY_QUALITY = 0.04  # in the word list but never seen as an answer


def _matches(pattern: str, word: str) -> bool:
    return all(p == "." or p == c for p, c in zip(pattern, word))


class CandidateProvider:
    def __init__(self, wordlist: WordList, clue_db: ClueDB | None = None) -> None:
        self.wordlist = wordlist
        self.clue_db = clue_db
        self._freq = clue_db.frequencies() if clue_db else None
        self._clue_cache: dict[str, dict[str, float]] = {}  # clue -> {answer: conf}
        self._scored_cache: dict[tuple[str, str], list[tuple[str, float]]] = {}

    def _clue_scores(self, clue: str) -> dict[str, float]:
        cached = self._clue_cache.get(clue)
        if cached is None:
            cached = dict(self.clue_db.lookup(clue)) if (clue and self.clue_db) else {}
            self._clue_cache[clue] = cached
        return cached

    def _quality(self, word: str) -> float:
        if self._freq is not None:
            q = quality_from_frequency(self._freq.get(word, 0))
            if q == 0.0 and word in self.wordlist.scores:
                return _WORDLIST_ONLY_QUALITY
            return q
        return normalized(self.wordlist.scores.get(word, DEFAULT_SCORE))

    def _score(self, word: str, clue_scores: dict[str, float]) -> float:
        quality = _QUALITY_FLOOR + _QUALITY_WEIGHT * self._quality(word)
        return max(clue_scores.get(word, 0.0), quality)

    def scored_candidates(self, entry: Entry, pattern: str) -> list[tuple[str, float]]:
        """Candidates matching `pattern` as (word, score), best score first."""
        key = (entry.clue, pattern)
        cached = self._scored_cache.get(key)
        if cached is not None:
            return cached

        length = len(pattern)
        clue_scores = self._clue_scores(entry.clue)
        words: dict[str, None] = {}
        for word in clue_scores:
            if len(word) == length and _matches(pattern, word):
                words[word] = None
        for word in self.wordlist.match(pattern):
            words[word] = None

        scored = [(w, self._score(w, clue_scores)) for w in words]
        scored.sort(key=lambda ws: ws[1], reverse=True)
        self._scored_cache[key] = scored
        return scored

    def candidates(self, entry: Entry, pattern: str) -> list[str]:
        return [w for w, _ in self.scored_candidates(entry, pattern)]

    def confidence(self, entry: Entry, word: str) -> float:
        """0..1 score for a chosen answer (clue match vs quality prior)."""
        return self._score(word, self._clue_scores(entry.clue))

    def top_clue_answer(self, entry: Entry) -> tuple[str, float] | None:
        """Best clue-database answer of this slot's length, as (word, confidence).

        The clue signal alone, independent of the grid fill -- used to surface the
        answers we're sure of even when the whole grid can't be solved.
        """
        best: tuple[str, float] | None = None
        for answer, conf in self._clue_scores(entry.clue).items():
            if len(answer) == entry.length and (best is None or conf > best[1]):
                best = (answer, conf)
        return best

    def is_valid_fill(self, word: str) -> bool:
        if word in self.wordlist.scores:
            return True
        return self.clue_db.is_known_answer(word) if self.clue_db else False
