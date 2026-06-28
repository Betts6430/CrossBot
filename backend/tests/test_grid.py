"""Slot derivation / numbering."""

from app.solver.grid import derive_entries


def test_open_three_by_three() -> None:
    cells = [["", "", ""], ["", "", ""], ["", "", ""]]
    entries = derive_entries(cells)
    # 3 across + 3 down. Across entries on lower rows take the next free number,
    # so row 1 -> 4A and row 2 -> 5A (standard crossword numbering).
    assert {e.id for e in entries} == {"1A", "1D", "2D", "3D", "4A", "5A"}
    assert all(e.length == 3 for e in entries)


def test_numbering_with_center_block() -> None:
    # . . .
    # . # .
    # . . .
    cells = [["", "", ""], ["", None, ""], ["", "", ""]]
    entries = derive_entries(cells)
    ids = sorted(e.id for e in entries)
    assert ids == ["1A", "1D", "2D", "3A"]
    by_id = {e.id: e for e in entries}
    assert by_id["1A"].cells == ((0, 0), (0, 1), (0, 2))
    assert by_id["1D"].cells == ((0, 0), (1, 0), (2, 0))
    assert by_id["2D"].cells == ((0, 2), (1, 2), (2, 2))
    assert by_id["3A"].cells == ((2, 0), (2, 1), (2, 2))
