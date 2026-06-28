"""CSP fill on small grids with an in-memory word list."""

from app.solver.csp import Solver
from app.solver.grid import derive_entries
from app.solver.wordlist import WordList

WORDS = ["CAT", "ARE", "TEN", "DOG", "EAR", "OLD", "ICE", "ACE", "TIE", "ANT"]


def _wordlist() -> WordList:
    return WordList.from_pairs((w, 50.0) for w in WORDS)


def test_fills_open_square() -> None:
    cells = [["", "", ""], ["", "", ""], ["", "", ""]]
    entries = derive_entries(cells)
    solver = Solver(cells, entries, _wordlist(), time_limit=5.0)

    assert solver.solve() is True
    # Every cell is filled...
    assert len(solver.fill) == 9
    # ...and every across/down entry is a real word.
    for entry in entries:
        word = "".join(solver.fill[cell] for cell in entry.cells)
        assert word in WORDS


def test_respects_given_letters() -> None:
    # Force the top-left letter; the solution must keep it. "C" completes to the
    # CAT/ARE/TEN word square with this list.
    cells = [["C", "", ""], ["", "", ""], ["", "", ""]]
    entries = derive_entries(cells)
    solver = Solver(cells, entries, _wordlist(), time_limit=5.0)

    assert solver.solve() is True
    assert solver.fill[(0, 0)] == "C"


def test_validates_crossing_entries() -> None:
    # Open 2x2. The only across fills are AB/CD, which force the down entries to
    # be AC/BD or CA/DB. With just AB and CD in the list, every down entry is a
    # non-word, so there is no valid fill -- the solver must NOT report success
    # just because all cells happen to be filled.
    cells = [["", ""], ["", ""]]
    entries = derive_entries(cells)
    wl = WordList.from_pairs((w, 50.0) for w in ["AB", "CD"])
    assert Solver(cells, entries, wl, time_limit=2.0).solve() is False

    # Add the needed down words and it becomes solvable, all entries valid.
    wl2 = WordList.from_pairs((w, 50.0) for w in ["AB", "CD", "AC", "BD"])
    solver = Solver(cells, entries, wl2, time_limit=2.0)
    assert solver.solve() is True
    for entry in entries:
        word = "".join(solver.fill[cell] for cell in entry.cells)
        assert word in wl2.scores


def test_unsatisfiable_returns_false() -> None:
    # The list only has 3-letter words; this grid needs length-2 (across) and
    # length-4 (down) entries, so it cannot be fully solved.
    cells = [["", ""], ["", ""], ["", ""], ["", ""]]
    entries = derive_entries(cells)
    solver = Solver(cells, entries, _wordlist(), time_limit=2.0)

    assert solver.solve() is False
