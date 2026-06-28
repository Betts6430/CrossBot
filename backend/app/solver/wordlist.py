"""The scored word list and fast pattern matching.

A `WordList` groups entries by length and builds an inverted index
`(position, letter) -> {words}` per length, so that finding every word that
matches a partial pattern like ``"A.C.."`` is a few set intersections.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


class WordList:
    def __init__(self) -> None:
        # UPPERCASE word -> quality score (0..100).
        self.scores: dict[str, float] = {}
        # length -> words of that length, sorted by score (best first).
        self.by_length: dict[int, list[str]] = {}
        # length -> (position, letter) -> set of words.
        self._index: dict[int, dict[tuple[int, str], set[str]]] = {}
        # pattern -> matches, memoized across a solve (big speedup).
        self._cache: dict[str, list[str]] = {}

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[str, float]]) -> "WordList":
        wl = cls()
        wl._build(pairs)
        return wl

    def _build(self, pairs: Iterable[tuple[str, float]]) -> None:
        buckets: dict[int, list[str]] = defaultdict(list)
        for raw, score in pairs:
            word = raw.strip().upper()
            if not word.isalpha():
                continue
            if word in self.scores:
                self.scores[word] = max(self.scores[word], float(score))
                continue
            self.scores[word] = float(score)
            buckets[len(word)].append(word)

        for length, words in buckets.items():
            words.sort(key=lambda w: self.scores[w], reverse=True)
            self.by_length[length] = words
            index: dict[tuple[int, str], set[str]] = defaultdict(set)
            for word in words:
                for pos, ch in enumerate(word):
                    index[(pos, ch)].add(word)
            self._index[length] = index

    def match(self, pattern: str) -> list[str]:
        """Words matching `pattern` ('.' = wildcard), best score first."""
        cached = self._cache.get(pattern)
        if cached is not None:
            return cached

        length = len(pattern)
        words = self.by_length.get(length)
        if not words:
            self._cache[pattern] = []
            return []

        fixed = [(i, ch) for i, ch in enumerate(pattern) if ch != "."]
        if not fixed:
            # Whole bucket, already score-sorted. Safe to share by reference.
            self._cache[pattern] = words
            return words

        index = self._index[length]
        sets: list[set[str]] = []
        for key in fixed:
            s = index.get(key)
            if not s:
                self._cache[pattern] = []
                return []
            sets.append(s)
        sets.sort(key=len)
        acc = set(sets[0])
        for s in sets[1:]:
            acc &= s
            if not acc:
                break
        result = sorted(acc, key=lambda w: self.scores[w], reverse=True)
        self._cache[pattern] = result
        return result

    def __len__(self) -> int:
        return len(self.scores)
