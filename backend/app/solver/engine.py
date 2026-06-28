"""Top-level orchestration of the solve.

Pipeline (see docs/ARCHITECTURE.md):
    1. candidates.generate(puzzle)  -> ranked answers per slot
       (clue-answer database lookup + scored word list)
    2. csp.solve(puzzle, candidates) -> globally consistent grid fill
    3. (optional) llm.boost(...) for slots still unresolved, if enabled

Not implemented yet — this file is scaffolding.
"""

from __future__ import annotations

from app.models import Puzzle, SolveResult


def solve_puzzle(puzzle: Puzzle) -> SolveResult:
    """Solve a puzzle end to end. Stub until the engine is built."""
    raise NotImplementedError(
        "Solver not implemented yet — see docs/ARCHITECTURE.md section 9 (roadmap)."
    )
