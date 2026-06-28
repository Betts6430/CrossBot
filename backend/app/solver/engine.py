"""Top-level orchestration of a solve.

MVP pipeline (see docs/ARCHITECTURE.md):
    1. derive entries from the grid (or use those the puzzle already carries)
    2. CSP fill using word-list candidates
    (clue-answer database and optional LLM booster come later)
"""

from __future__ import annotations

from app.data.loaders import get_wordlist
from app.models import Puzzle, SlotAnswer, SolveResult
from app.solver.csp import Solver
from app.solver.grid import Coord, Entry, derive_entries
from app.solver.scoring import DEFAULT_SCORE, normalized


def _entries_for(puzzle: Puzzle) -> list[Entry]:
    """Use the puzzle's own slots if present, else derive them from the grid."""
    if puzzle.slots:
        return [
            Entry(s.id, s.number, s.direction, tuple((r, c) for r, c in s.cells))
            for s in puzzle.slots
        ]
    return derive_entries(puzzle.cells)


def solve_puzzle(puzzle: Puzzle) -> SolveResult:
    """Solve a puzzle end to end and return the filled grid + per-slot answers."""
    wordlist = get_wordlist()
    entries = _entries_for(puzzle)

    solver = Solver(puzzle.cells, entries, wordlist)
    solver.solve()
    fill: dict[Coord, str] = solver.result_fill()

    filled: list[list[str | None]] = []
    for r, row in enumerate(puzzle.cells):
        out_row: list[str | None] = []
        for c, value in enumerate(row):
            if value is None:
                out_row.append(None)
            else:
                out_row.append(fill.get((r, c), value if isinstance(value, str) else ""))
        filled.append(out_row)

    answers: list[SlotAnswer] = []
    complete = True
    for entry in entries:
        letters = [fill.get(cell) for cell in entry.cells]
        if all(letters):
            word = "".join(letters)  # type: ignore[arg-type]
            score = wordlist.scores.get(word, DEFAULT_SCORE)
            answers.append(
                SlotAnswer(id=entry.id, answer=word, confidence=normalized(score))
            )
        else:
            complete = False
            answers.append(SlotAnswer(id=entry.id, answer=None, confidence=0.0))

    if solver.solved and complete:
        status = "solved"
    elif any(a.answer for a in answers):
        status = "partial"
    else:
        status = "failed"

    return SolveResult(status=status, filled=filled, answers=answers)
