"""Clue database build + query, on a tiny in-memory corpus."""

from pathlib import Path

import pytest

from app.data.clue_db import ClueDB, build_clue_db, clean_answer, normalize_clue

USAGES = [
    ("CAT", "Feline pet"),
    ("CAT", "Feline pet"),  # repeated -> higher exact count
    ("CAT", "Purring animal"),
    ("DOG", "Canine pet"),
    ("DOG", "Loyal pet"),
    ("1UP", "Video game life"),  # non-alpha answer -> dropped
    ("ARE", "Exist"),
]


@pytest.fixture
def db(tmp_path: Path) -> ClueDB:
    path = tmp_path / "clues.sqlite"
    kept = build_clue_db(USAGES, path)
    assert kept == 6  # the 1UP usage is dropped
    return ClueDB.open(path)


def test_normalize_clue() -> None:
    assert normalize_clue("  Feline, PET! ") == "feline pet"
    assert normalize_clue("THX ___ (film)") == "thx film"


def test_clean_answer() -> None:
    assert clean_answer(" cat ") == "CAT"
    assert clean_answer("1UP") is None
    assert clean_answer("A") is None  # too short


def test_exact_lookup_ranks_by_frequency(db: ClueDB) -> None:
    results = db.lookup("feline pet")
    assert results, "expected a match"
    assert results[0][0] == "CAT"
    assert results[0][1] > 0.9  # exact match -> high confidence


def test_fuzzy_lookup_finds_related(db: ClueDB) -> None:
    # No exact clue "Beloved pet", but it shares the token "pet".
    answers = [a for a, _ in db.lookup("Beloved pet")]
    assert "CAT" in answers or "DOG" in answers


def test_is_known_answer(db: ClueDB) -> None:
    assert db.is_known_answer("CAT")
    assert db.is_known_answer("DOG")
    assert not db.is_known_answer("ZZZZZ")
    assert not db.is_known_answer("1UP")  # was filtered out


def test_lookup_many_matches_serial(db: ClueDB) -> None:
    # Parallel batch lookup must return exactly what serial lookups would, keyed
    # by clue (duplicates collapsed).
    clues = ["feline pet", "Beloved pet", "Canine pet", "feline pet"]
    batch = db.lookup_many(clues, max_workers=4)
    assert set(batch) == {"feline pet", "Beloved pet", "Canine pet"}
    for clue, scored in batch.items():
        assert scored == db.lookup(clue)


def test_lookup_many_without_path_falls_back(db: ClueDB) -> None:
    # An in-memory handle (no path) can't open per-thread connections; it should
    # still answer correctly, just serially.
    handle = ClueDB(db.conn)  # no path
    assert handle.path is None
    assert handle.lookup_many(["feline pet"]) == {"feline pet": db.lookup("feline pet")}
