"""CandidateProvider: clue answers come first and a clued solve prefers them."""

from pathlib import Path

import pytest

from app.data.clue_db import ClueDB, build_clue_db
from app.solver.candidates import CandidateProvider
from app.solver.csp import Solver
from app.solver.grid import Entry, derive_entries
from app.solver.wordlist import WordList


@pytest.fixture
def clue_db(tmp_path: Path) -> ClueDB:
    path = tmp_path / "clues.sqlite"
    build_clue_db([("CAT", "Feline"), ("CAT", "Feline")], path)
    return ClueDB.open(path)


def test_clue_answers_come_first(clue_db: ClueDB) -> None:
    # COT scores higher than CAT in the word list, but the clue points to CAT.
    wl = WordList.from_pairs([("COT", 90.0), ("CAT", 10.0), ("CUT", 80.0)])
    provider = CandidateProvider(wl, clue_db)

    entry = Entry("1A", 1, "across", ((0, 0), (0, 1), (0, 2)), clue="Feline")
    cands = provider.candidates(entry, "...")
    assert cands[0] == "CAT"  # clue answer beats higher word-list score
    assert provider.confidence(entry, "CAT") > 0.9


def test_no_clue_falls_back_to_wordlist(clue_db: ClueDB) -> None:
    wl = WordList.from_pairs([("COT", 90.0), ("CAT", 10.0)])
    provider = CandidateProvider(wl, clue_db)

    entry = Entry("1A", 1, "across", ((0, 0), (0, 1), (0, 2)), clue="")
    cands = provider.candidates(entry, "...")
    assert cands[0] == "COT"  # no clue -> best word-list score wins


def test_clued_single_slot_solve_prefers_db_answer(clue_db: ClueDB) -> None:
    wl = WordList.from_pairs([("COT", 90.0), ("CAT", 10.0), ("CUT", 80.0)])
    provider = CandidateProvider(wl, clue_db)

    cells = [["", "", ""]]
    [entry] = derive_entries(cells)
    clued = Entry(entry.id, entry.number, entry.direction, entry.cells, clue="Feline")

    solver = Solver(cells, [clued], provider, time_limit=2.0)
    assert solver.solve() is True
    assert "".join(solver.fill[c] for c in clued.cells) == "CAT"
