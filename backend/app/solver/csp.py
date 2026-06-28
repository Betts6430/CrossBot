"""Constraint-satisfaction grid fill.

Each entry is a variable; crossing cells are the constraints. We do depth-first
backtracking with:
  - MRV (minimum remaining values): always branch on the entry with the fewest
    candidates, which also gives forward-checking for free (an entry with zero
    candidates fails the branch immediately), and
  - candidates tried best-score-first, capped by a beam width.

A time/node budget bounds the search; if it can't fully solve in budget it
returns the deepest (most-filled) partial assignment it found.
"""

from __future__ import annotations

import time

from app.solver.candidates import slot_candidates
from app.solver.grid import Cell, Coord, Entry
from app.solver.wordlist import WordList


class Solver:
    def __init__(
        self,
        cells: list[list[Cell]],
        entries: list[Entry],
        wordlist: WordList,
        *,
        beam: int = 50,
        time_limit: float = 15.0,
        node_limit: int = 500_000,
    ) -> None:
        self.entries = entries
        self.wordlist = wordlist
        self.beam = beam
        self.time_limit = time_limit
        self.node_limit = node_limit

        # Working assignment: cell -> letter. Seeded with the given letters.
        self.fill: dict[Coord, str] = {}
        for r, row in enumerate(cells):
            for c, value in enumerate(row):
                if isinstance(value, str) and value != "":
                    self.fill[(r, c)] = value.upper()

        self.solved = False
        self.nodes = 0
        self._start = 0.0
        # Best (most-filled) partial seen, for graceful timeouts.
        self.best_fill: dict[Coord, str] = dict(self.fill)

    def _pattern(self, entry: Entry) -> str:
        return "".join(self.fill.get(cell, ".") for cell in entry.cells)

    def _out_of_budget(self) -> bool:
        return (
            self.nodes > self.node_limit
            or (time.monotonic() - self._start) > self.time_limit
        )

    def solve(self) -> bool:
        self._start = time.monotonic()
        self.solved = self._recurse()
        return self.solved

    def _recurse(self) -> bool:
        self.nodes += 1
        if self._out_of_budget():
            return False

        # Pick the unfilled entry with the fewest candidates (MRV).
        target: Entry | None = None
        target_cands: list[str] | None = None
        for entry in self.entries:
            pattern = self._pattern(entry)
            if "." not in pattern:
                # Fully determined (possibly only by crossing letters) — it must
                # itself be a real word, otherwise this branch is a dead end.
                if pattern not in self.wordlist.scores:
                    return False
                continue
            cands = slot_candidates(self.wordlist, pattern)
            if not cands:
                return False  # dead end: nothing fits here
            if target_cands is None or len(cands) < len(target_cands):
                target, target_cands = entry, cands
                if len(cands) == 1:
                    break

        if target is None:
            return True  # every entry filled -> solved

        if len(self.fill) > len(self.best_fill):
            self.best_fill = dict(self.fill)

        assert target_cands is not None
        for word in target_cands[: self.beam]:
            changed: list[Coord] = []
            for cell, ch in zip(target.cells, word):
                if cell not in self.fill:
                    self.fill[cell] = ch
                    changed.append(cell)
            if self._recurse():
                return True
            for cell in changed:
                del self.fill[cell]
            if self._out_of_budget():
                return False

        return False

    def result_fill(self) -> dict[Coord, str]:
        """The final assignment: complete if solved, else the best partial."""
        return self.fill if self.solved else self.best_fill
