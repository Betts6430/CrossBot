"""HTTP routes for the solver."""

from __future__ import annotations

from fastapi import APIRouter

from app.models import Puzzle, SolveResult
from app.solver.engine import solve_puzzle

router = APIRouter()


@router.post("/solve", response_model=SolveResult)
def solve(puzzle: Puzzle) -> SolveResult:
    """Solve (autocomplete) a puzzle and return the filled grid."""
    return solve_puzzle(puzzle)
