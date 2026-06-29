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

from typing import Iterable

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
        self._extra: dict[str, dict[str, float]] = {}  # slot id -> {answer: conf}

    def add_candidates(self, entry_id: str, answers: Iterable[tuple[str, float]]) -> None:
        """Inject extra scored answers for one slot (e.g. from the LLM booster).

        They're scored alongside clue/word-list candidates; the highest score for a
        word wins. Clears the scored cache so a re-solve picks them up.
        """
        store = self._extra.setdefault(entry_id, {})
        for word, conf in answers:
            store[word] = max(store.get(word, 0.0), conf)
        self._scored_cache.clear()

    def prime_clues(self, clues: Iterable[str]) -> None:
        """Warm the clue cache for many clues in one parallel batch.

        The per-clue lookups are otherwise driven lazily by candidate generation,
        one at a time; priming them together up front is much faster on big grids.
        """
        if not self.clue_db:
            return
        todo = [c for c in dict.fromkeys(clues) if c and c not in self._clue_cache]
        if not todo:
            return
        for clue, scored in self.clue_db.lookup_many(todo).items():
            self._clue_cache[clue] = dict(scored)

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

    def _score(
        self, word: str, clue_scores: dict[str, float], extra: dict[str, float] | None
    ) -> float:
        quality = _QUALITY_FLOOR + _QUALITY_WEIGHT * self._quality(word)
        score = max(clue_scores.get(word, 0.0), quality)
        if extra is not None:
            score = max(score, extra.get(word, 0.0))
        return score

    def scored_candidates(self, entry: Entry, pattern: str) -> list[tuple[str, float]]:
        """Candidates matching `pattern` as (word, score), best score first."""
        key = (entry.id, pattern)  # per-slot: injected extras are keyed by slot id
        cached = self._scored_cache.get(key)
        if cached is not None:
            return cached

        length = len(pattern)
        clue_scores = self._clue_scores(entry.clue)
        extra = self._extra.get(entry.id)
        words: dict[str, None] = {}
        for source in (clue_scores, extra) if extra else (clue_scores,):
            for word in source:
                if len(word) == length and _matches(pattern, word):
                    words[word] = None
        for word in self.wordlist.match(pattern):
            words[word] = None

        scored = [(w, self._score(w, clue_scores, extra)) for w in words]
        scored.sort(key=lambda ws: ws[1], reverse=True)
        self._scored_cache[key] = scored
        return scored

    def candidates(self, entry: Entry, pattern: str) -> list[str]:
        return [w for w, _ in self.scored_candidates(entry, pattern)]

    def confidence(self, entry: Entry, word: str) -> float:
        """0..1 score for a chosen answer (clue/LLM match vs quality prior)."""
        return self._score(word, self._clue_scores(entry.clue), self._extra.get(entry.id))

    def base_confidence(self, entry: Entry, word: str) -> float:
        """Confidence from clue DB + quality only, ignoring injected (LLM) answers.

        Lets the painter tell a clue-corroborated cell from one an LLM merely
        guessed, so the booster's own guesses paint only with corroboration.
        """
        return self._score(word, self._clue_scores(entry.clue), None)

    def top_clue_answer(self, entry: Entry) -> tuple[str, float] | None:
        """Best clue-database answer of this slot's length, as (word, confidence).

        The clue signal alone, independent of the grid fill -- used to anchor the
        paint even when the whole grid can't be solved. (LLM answers are *not*
        anchors; they paint only via the corroboration tier in the engine.)
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
