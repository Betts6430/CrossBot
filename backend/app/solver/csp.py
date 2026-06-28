"""Constraint-satisfaction fill.

Treats the grid as a CSP: each slot is a variable, each shared (crossing) cell
is a constraint that the intersecting letters must agree. Uses constraint
propagation + weighted backtracking, preferring higher-scored candidates, to
produce a globally consistent fill.

This is the core "autocomplete the grid" engine. Not implemented yet.
"""

from __future__ import annotations

from app.models import Puzzle, SolveResult


def solve(
    puzzle: Puzzle,
    candidates: dict[str, list[tuple[str, float]]],
) -> SolveResult:
    """Choose a globally consistent fill from per-slot candidates."""
    raise NotImplementedError
