"""Pydantic mirror of shared/puzzle.schema.json.

Keep this in sync with extension/lib/model/puzzle.ts when the schema changes.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# A grid cell: None = block, "" = empty fillable, "A"… = a given letter.
Cell = str | None

# A (row, col) coordinate, zero-indexed from the top-left.
Coord = tuple[int, int]

Direction = Literal["across", "down"]


class Slot(BaseModel):
    """One answer position (an across or down entry)."""

    id: str
    number: int
    direction: Direction
    cells: list[Coord]
    length: int
    clue: str


class Puzzle(BaseModel):
    """A normalized crossword. Produced by adapters, manual entry, or import."""

    source: str | None = None
    title: str | None = None
    width: int
    height: int
    cells: list[list[Cell]]
    slots: list[Slot]


class SlotAnswer(BaseModel):
    """The solver's answer for a single slot."""

    id: str
    answer: str | None
    confidence: float = Field(ge=0.0, le=1.0)


class SolveResult(BaseModel):
    """What POST /solve returns. Consumed by the overlay / popup UI."""

    status: Literal["solved", "partial", "failed"]
    filled: list[list[Cell]]
    answers: list[SlotAnswer]
