"""CSP fill on small grids with an in-memory word list (no clue DB)."""

from app.solver.candidates import CandidateProvider
from app.solver.csp import Solver
from app.solver.grid import derive_entries
from app.solver.wordlist import WordList

WORDS = ["CAT", "ARE", "TEN", "DOG", "EAR", "OLD", "ICE", "ACE", "TIE", "ANT"]


def _provider(words=WORDS) -> CandidateProvider:
    return CandidateProvider(WordList.from_pairs((w, 50.0) for w in words))


def test_fills_open_square() -> None:
    cells = [["", "", ""], ["", "", ""], ["", "", ""]]
    entries = derive_entries(cells)
    solver = Solver(cells, entries, _provider(), time_limit=5.0)

    assert solver.solve() is True
    assert len(solver.fill) == 9
    for entry in entries:
        word = "".join(solver.fill[cell] for cell in entry.cells)
        assert word in WORDS


def test_respects_given_letters() -> None:
    # "C" completes to the CAT/ARE/TEN word square with this list.
    cells = [["C", "", ""], ["", "", ""], ["", "", ""]]
    entries = derive_entries(cells)
    solver = Solver(cells, entries, _provider(), time_limit=5.0)

    assert solver.solve() is True
    assert solver.fill[(0, 0)] == "C"


def test_validates_crossing_entries() -> None:
    # Open 2x2. With only AB/CD, the down entries are forced to non-words, so
    # there is no valid fill -- the solver must not report success just because
    # all cells are filled.
    cells = [["", ""], ["", ""]]
    entries = derive_entries(cells)
    assert Solver(cells, entries, _provider(["AB", "CD"]), time_limit=2.0).solve() is False

    # Add the needed down words and it becomes solvable, all entries valid.
    provider = _provider(["AB", "CD", "AC", "BD"])
    solver = Solver(cells, entries, provider, time_limit=2.0)
    assert solver.solve() is True
    for entry in entries:
        word = "".join(solver.fill[cell] for cell in entry.cells)
        assert provider.is_valid_fill(word)


def test_unsatisfiable_returns_false() -> None:
    # The list only has 3-letter words; this grid needs length-2 (across) and
    # length-4 (down) entries, so it cannot be fully solved.
    cells = [["", ""], ["", ""], ["", ""], ["", ""]]
    entries = derive_entries(cells)
    solver = Solver(cells, entries, _provider(), time_limit=2.0)

    assert solver.solve() is False
