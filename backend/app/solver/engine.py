"""Top-level orchestration of a solve.

Pipeline (see docs/ARCHITECTURE.md):
    1. derive entries from the grid (or use those the puzzle carries, with clues)
    2. CSP fill using a CandidateProvider = clue database + word list
    (the optional LLM booster comes later)
"""

from __future__ import annotations

from app.data.loaders import get_clue_db, get_wordlist
from app.models import Puzzle, SlotAnswer, SolveResult
from app.solver.candidates import CandidateProvider
from app.solver.csp import Solver
from app.solver.grid import Coord, Entry, derive_entries


def _entries_for(puzzle: Puzzle) -> list[Entry]:
    """Use the puzzle's own slots (with clues) if present, else derive them."""
    if puzzle.slots:
        return [
            Entry(s.id, s.number, s.direction, tuple((r, c) for r, c in s.cells), s.clue)
            for s in puzzle.slots
        ]
    return derive_entries(puzzle.cells)


def solve_puzzle(puzzle: Puzzle) -> SolveResult:
    """Solve a puzzle end to end and return the filled grid + per-slot answers."""
    provider = CandidateProvider(get_wordlist(), get_clue_db())
    entries = _entries_for(puzzle)

    solver = Solver(puzzle.cells, entries, provider)
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
            answers.append(
                SlotAnswer(id=entry.id, answer=word, confidence=provider.confidence(entry, word))
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
