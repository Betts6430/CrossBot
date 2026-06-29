"""CandidateProvider scoring + the solver picking the clue-consistent grid."""

from pathlib import Path

import pytest

from app.data.clue_db import ClueDB, build_clue_db
from app.solver.candidates import CandidateProvider
from app.solver.csp import Solver
from app.solver.grid import Entry, derive_entries
from app.solver.wordlist import WordList


@pytest.fixture
def feline_db(tmp_path: Path) -> ClueDB:
    path = tmp_path / "clues.sqlite"
    build_clue_db([("CAT", "Feline"), ("CAT", "Feline")], path)
    return ClueDB.open(path)


def test_clue_answers_come_first(feline_db: ClueDB) -> None:
    wl = WordList.from_pairs([("COT", 90.0), ("CAT", 10.0), ("CUT", 80.0)])
    provider = CandidateProvider(wl, feline_db)

    entry = Entry("1A", 1, "across", ((0, 0), (0, 1), (0, 2)), clue="Feline")
    cands = provider.candidates(entry, "...")
    assert cands[0] == "CAT"  # clue answer beats higher word-list score
    assert provider.confidence(entry, "CAT") > 0.9


def test_no_clue_ranks_by_crossword_frequency(tmp_path: Path) -> None:
    # COT is a far more common crossword answer than CAT in this corpus.
    path = tmp_path / "c.sqlite"
    build_clue_db([("COT", "Bed")] * 5 + [("CAT", "Pet")], path)
    db = ClueDB.open(path)
    # Word-list scores are intentionally "wrong"; frequency should drive ranking.
    wl = WordList.from_pairs([("COT", 10.0), ("CAT", 90.0)])
    provider = CandidateProvider(wl, db)

    entry = Entry("1A", 1, "across", ((0, 0), (0, 1), (0, 2)), clue="")
    assert provider.candidates(entry, "...")[0] == "COT"


def test_clued_single_slot_prefers_db_answer(feline_db: ClueDB) -> None:
    wl = WordList.from_pairs([("COT", 90.0), ("CAT", 10.0), ("CUT", 80.0)])
    provider = CandidateProvider(wl, feline_db)

    cells = [["", "", ""]]
    [entry] = derive_entries(cells)
    clued = Entry(entry.id, entry.number, entry.direction, entry.cells, clue="Feline")

    solver = Solver(cells, [clued], provider, time_limit=2.0)
    assert solver.solve() is True
    assert "".join(solver.fill[c] for c in clued.cells) == "CAT"


def test_prefers_clue_consistent_grid(tmp_path: Path) -> None:
    # Open 2x2 with two valid squares. The clue on 1A should pull the solver to
    # the grid where 1A is its clue answer (HI) -- the key quality fix: a strong
    # clue answer wins even though either square is a consistent fill.
    path = tmp_path / "c.sqlite"
    build_clue_db([("HI", "Greeting"), ("HI", "Greeting")], path)
    db = ClueDB.open(path)
    wl = WordList.from_pairs([(w, 50.0) for w in ["HI", "HO", "IT", "OT"]])
    provider = CandidateProvider(wl, db)

    cells = [["", ""], ["", ""]]
    entries = [
        Entry(e.id, e.number, e.direction, e.cells, "Greeting" if e.id == "1A" else "")
        for e in derive_entries(cells)
    ]

    solver = Solver(cells, entries, provider, time_limit=2.0)
    assert solver.solve() is True
    one_a = next(e for e in entries if e.id == "1A")
    assert "".join(solver.fill[c] for c in one_a.cells) == "HI"
