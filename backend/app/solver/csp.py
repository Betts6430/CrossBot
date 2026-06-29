"""Constraint-satisfaction grid fill: score-maximizing search with arc consistency.

Each entry is a variable whose domain is a scored list of candidate words; crossing
cells must agree. Two things make this tractable *and* good:

  - **Maintained arc consistency.** Each open cell carries the set of letters still
    possible. Choosing (or propagating) a word shrinks its cells' letter sets, which
    filters every crossing slot's candidate list, which can shrink further cells, to
    a fixpoint. Dead ends are caught far earlier than plain backtracking, so dense
    15x15 grids that thrash under forward-checking-only fill in hundreds of nodes.
  - **Score-maximizing branch-and-bound.** Candidates are tried best-score-first
    (clue answers beat generic fill), and we keep the highest *total* score complete
    fill rather than the first one found -- so an entry completed by crossings still
    prefers its own clue answer. An admissible bound (sum of each slot's best still-
    possible score) prunes branches that can't beat the incumbent.

A time/node budget bounds the search; after the first complete fill a tighter node
budget caps the improvement phase. On a timeout it returns the most-determined
partial (cells pinned to a single possible letter).
"""

from __future__ import annotations

import time

from app.solver.candidates import CandidateProvider
from app.solver.grid import Cell, Coord, Entry

_LETTERS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
# Keep at most this many (highest-scored) candidates per slot. Bounds propagation
# cost on short, lightly-constrained slots; far above any slot's count on minis.
_CANDIDATE_CAP = 2000


class Solver:
    def __init__(
        self,
        cells: list[list[Cell]],
        entries: list[Entry],
        provider: CandidateProvider,
        *,
        beam: int = 20,
        time_limit: float = 8.0,
        node_limit: int = 200_000,
        improve_nodes: int = 15_000,
        candidate_cap: int = _CANDIDATE_CAP,
    ) -> None:
        self.entries = entries
        self.provider = provider
        self.beam = beam
        self.time_limit = time_limit
        self.node_limit = node_limit
        self.improve_nodes = improve_nodes

        given: dict[Coord, str] = {}
        for r, row in enumerate(cells):
            for c, value in enumerate(row):
                if isinstance(value, str) and value != "":
                    given[(r, c)] = value.upper()
        self._given = given

        # cell -> [(slot index, position in that slot)]
        self.cell_slots: dict[Coord, list[tuple[int, int]]] = {}
        for si, e in enumerate(entries):
            for pos, cell in enumerate(e.cells):
                self.cell_slots.setdefault(cell, []).append((si, pos))

        # cell -> still-possible letters (a given letter pins its cell up front)
        self.domain: dict[Coord, set[str]] = {
            cell: {given[cell]} if cell in given else set(_LETTERS)
            for cell in self.cell_slots
        }

        # per-slot candidate list: (word, score), best score first, capped
        self.cands: list[list[tuple[str, float]]] = []
        for e in entries:
            pattern = "".join(given.get(cell, ".") for cell in e.cells)
            scored = provider.scored_candidates(e, pattern)
            self.cands.append(list(scored[:candidate_cap]))

        self.best_total = float("-inf")
        self.best_assignment: dict[str, tuple[str, float]] = {}
        self._best_complete: dict[Coord, str] | None = None
        self._best_partial: dict[Coord, str] = dict(given)
        self._max_determined = len(given)

        self.fill: dict[Coord, str] = dict(given)
        self.solved = False
        self.nodes = 0
        self._start = 0.0
        self._nodes_at_first: int | None = None

    # -- public API ---------------------------------------------------------

    def solve(self) -> bool:
        self._start = time.monotonic()
        # A slot with no candidates at all (e.g. no word of its length) makes the
        # grid infeasible up front. Otherwise run initial arc consistency, which is
        # permanent (no trail); if it wipes a slot we keep the best partial.
        if all(self.cands) and self._propagate(list(range(len(self.entries))), {}, {}):
            self._record_partial()
            self._search()
        self.solved = self._best_complete is not None
        self.fill = self.result_fill()
        return self.solved

    def result_fill(self) -> dict[Coord, str]:
        return self._best_complete if self._best_complete is not None else self._best_partial

    # -- search -------------------------------------------------------------

    def _out_of_budget(self) -> bool:
        if self.nodes > self.node_limit:
            return True
        if (time.monotonic() - self._start) > self.time_limit:
            return True
        if (
            self._nodes_at_first is not None
            and self.nodes - self._nodes_at_first > self.improve_nodes
        ):
            return True
        return False

    def _search(self) -> None:
        self.nodes += 1
        if self._out_of_budget():
            return

        # One pass: admissible bound (sum of each slot's best still-possible score),
        # MRV target (fewest candidates among undecided slots), and decided count.
        upper = 0.0
        target = -1
        fewest = 0
        decided = 0
        for si, cl in enumerate(self.cands):
            upper += cl[0][1]
            n = len(cl)
            if n == 1:
                decided += 1
            elif target == -1 or n < fewest:
                target, fewest = si, n

        if upper <= self.best_total:
            return  # cannot beat the incumbent complete fill

        if target == -1:  # every slot decided -> a complete fill, score == upper
            if upper > self.best_total:
                self.best_total = upper
                self._best_complete = self._fill_from_cands()
                self.best_assignment = {e.id: self.cands[i][0] for i, e in enumerate(self.entries)}
            if self._nodes_at_first is None:
                self._nodes_at_first = self.nodes
            return

        if decided > self._max_determined:
            self._record_partial(decided)

        for word, score in self.cands[target][: self.beam]:
            trail_cands: dict[int, list[tuple[str, float]]] = {target: self.cands[target]}
            trail_dom: dict[Coord, set[str]] = {}
            self.cands[target] = [(word, score)]

            queue: list[int] = []
            ok = True
            for pos, cell in enumerate(self.entries[target].cells):
                d = self.domain[cell]
                if word[pos] not in d:
                    ok = False
                    break
                if len(d) > 1:
                    trail_dom.setdefault(cell, d)
                    self.domain[cell] = {word[pos]}
                    queue.extend(sj for sj, _ in self.cell_slots[cell] if sj != target)

            if ok and self._propagate(queue, trail_cands, trail_dom):
                self._search()

            for si, old in trail_cands.items():
                self.cands[si] = old
            for cell, old in trail_dom.items():
                self.domain[cell] = old

            if self._out_of_budget():
                break

    def _propagate(
        self,
        queue: list[int],
        trail_cands: dict[int, list[tuple[str, float]]],
        trail_dom: dict[Coord, set[str]],
    ) -> bool:
        """Filter slots/cells to a fixpoint. False if any slot loses all candidates.

        Records originals into the trail dicts so the caller can undo; pass fresh
        throwaway dicts for the one-shot initial pass.
        """
        domain = self.domain
        while queue:
            si = queue.pop()
            cells = self.entries[si].cells
            cur = self.cands[si]
            new = [ws for ws in cur if all(ws[0][pos] in domain[cell] for pos, cell in enumerate(cells))]
            if len(new) == len(cur):
                continue
            if not new:
                return False
            trail_cands.setdefault(si, cur)
            self.cands[si] = new
            for pos, cell in enumerate(cells):
                d = domain[cell]
                if len(d) == 1:
                    continue
                allowed = {ws[0][pos] for ws in new}
                if d <= allowed:
                    continue
                nd = d & allowed
                if not nd:
                    return False
                trail_dom.setdefault(cell, d)
                domain[cell] = nd
                queue.extend(sj for sj, _ in self.cell_slots[cell] if sj != si)
        return True

    # -- result helpers -----------------------------------------------------

    def _fill_from_cands(self) -> dict[Coord, str]:
        out: dict[Coord, str] = {}
        for i, e in enumerate(self.entries):
            word = self.cands[i][0][0]
            for pos, cell in enumerate(e.cells):
                out[cell] = word[pos]
        return out

    def _record_partial(self, determined: int | None = None) -> None:
        """Snapshot every cell currently pinned to a single possible letter."""
        fill = {cell: next(iter(d)) for cell, d in self.domain.items() if len(d) == 1}
        if len(fill) >= self._max_determined:
            self._max_determined = len(fill)
            self._best_partial = fill
