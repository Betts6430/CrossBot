"""HTTP routes for the solver."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import Puzzle, SolveResult
from app.solver.engine import solve_puzzle

router = APIRouter()


@router.post("/solve", response_model=SolveResult)
def solve(puzzle: Puzzle, boost: bool | None = None) -> SolveResult:
    """Solve (autocomplete) a puzzle and return the filled grid.

    The ``boost`` query param opts the optional LLM booster in or out for this
    solve: omitted/``true`` uses it when the backend has one configured, ``false``
    skips it. It's a no-op unless a local model is set up (``CROSSBOT_LLM=ollama``).
    """
    return solve_puzzle(puzzle, boost=boost)
