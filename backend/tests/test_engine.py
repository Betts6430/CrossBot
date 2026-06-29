"""Engine: entry building, and confidence-gated painting (show only what we know)."""

from pathlib import Path

import pytest

import app.solver.engine as engine
from app.data.clue_db import ClueDB, build_clue_db
from app.models import ClueRef, Puzzle
from app.solver.engine import _entries_for
from app.solver.wordlist import WordList


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


def _use(monkeypatch: pytest.MonkeyPatch, db: ClueDB | None, words: list[str]) -> None:
    wl = WordList.from_pairs((w, 50.0) for w in words)
    monkeypatch.setattr(engine, "get_wordlist", lambda: wl)
    monkeypatch.setattr(engine, "get_clue_db", lambda: db)


def test_matched_clue_painted_but_unmatched_clue_left_blank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "c.sqlite"
    build_clue_db([("CAT", "Feline"), ("CAT", "Feline")], path)
    _use(monkeypatch, ClueDB.open(path), ["CAT", "COT", "CUT"])

    # A slot whose clue the database knows -> we paint that answer.
    known = Puzzle(width=3, height=1, cells=[["", "", ""]],
                   clues=[ClueRef(number=1, direction="across", clue="Feline")])
    res = engine.solve_puzzle(known)
    assert res.filled[0] == ["C", "A", "T"]
    assert res.status == "solved"

    # A clued slot the database can't match -> a quality-prior guess we don't trust,
    # so it's left blank rather than overlaying a confident-looking wrong answer.
    unknown = Puzzle(width=3, height=1, cells=[["", "", ""]],
                     clues=[ClueRef(number=1, direction="across", clue="zxqw not in corpus")])
    res = engine.solve_puzzle(unknown)
    assert res.filled[0] == ["", "", ""]
    assert res.status == "failed"


def test_unclued_grid_is_filled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Manual entry sends no clues; there's nothing to be unsure against, so the
    # best word-list fill is shown in full (the engine-MVP behavior).
    _use(monkeypatch, None, ["CAT", "COT", "CUT"])
    res = engine.solve_puzzle(Puzzle(width=3, height=1, cells=[["", "", ""]]))
    assert all(cell not in (None, "") for cell in res.filled[0])
    assert res.status == "solved"
