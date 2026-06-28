"""Grid helpers: deriving across/down entries from a bare grid.

The solver core works with plain `Entry` objects rather than the Pydantic API
models, so it has no web dependencies and is easy to unit-test.
"""

from __future__ import annotations

from dataclasses import dataclass

# A grid cell: None = block, "" = empty fillable, "A"… = a given letter.
Cell = str | None
Coord = tuple[int, int]


@dataclass(frozen=True)
class Entry:
    """One across or down answer position."""

    id: str
    number: int
    direction: str  # "across" | "down"
    cells: tuple[Coord, ...]

    @property
    def length(self) -> int:
        return len(self.cells)


def derive_entries(cells: list[list[Cell]]) -> list[Entry]:
    """Number the grid and extract every across/down entry (length >= 2).

    Standard crossword numbering: a cell starts an across entry when its left
    neighbour is a block/edge and its right neighbour is open, and likewise for
    down. Cells get numbered in reading order whenever a new entry begins.
    """
    height = len(cells)
    width = len(cells[0]) if height else 0
    entries: list[Entry] = []
    number = 0

    for r in range(height):
        for c in range(width):
            if cells[r][c] is None:
                continue

            left_block = c == 0 or cells[r][c - 1] is None
            right_open = c + 1 < width and cells[r][c + 1] is not None
            up_block = r == 0 or cells[r - 1][c] is None
            down_open = r + 1 < height and cells[r + 1][c] is not None

            starts_across = left_block and right_open
            starts_down = up_block and down_open
            if not (starts_across or starts_down):
                continue

            number += 1
            if starts_across:
                run: list[Coord] = []
                cc = c
                while cc < width and cells[r][cc] is not None:
                    run.append((r, cc))
                    cc += 1
                entries.append(Entry(f"{number}A", number, "across", tuple(run)))
            if starts_down:
                run = []
                rr = r
                while rr < height and cells[rr][c] is not None:
                    run.append((rr, c))
                    rr += 1
                entries.append(Entry(f"{number}D", number, "down", tuple(run)))

    return entries
