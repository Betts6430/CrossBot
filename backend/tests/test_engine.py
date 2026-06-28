"""Engine entry building: clues attach to derived entries by number+direction."""

from app.models import ClueRef, Puzzle
from app.solver.engine import _entries_for


def test_clues_attached_by_number_and_direction() -> None:
    cells = [["", "", ""], ["", "", ""], ["", "", ""]]
    puzzle = Puzzle(
        width=3,
        height=3,
        cells=cells,
        clues=[
            ClueRef(number=1, direction="across", clue="Feline"),
            ClueRef(number=1, direction="down", clue="Kitty"),
        ],
    )
    by_id = {e.id: e for e in _entries_for(puzzle)}
    assert by_id["1A"].clue == "Feline"
    assert by_id["1D"].clue == "Kitty"
    assert by_id["2D"].clue == ""  # no clue provided -> empty
