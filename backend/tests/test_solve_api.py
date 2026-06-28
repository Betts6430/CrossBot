"""POST /solve end to end, with a small injected word list."""

import pytest
from fastapi.testclient import TestClient

import app.solver.engine as engine
from app.main import app
from app.solver.wordlist import WordList

client = TestClient(app)


@pytest.fixture(autouse=True)
def _small_wordlist(monkeypatch: pytest.MonkeyPatch) -> None:
    words = ["CAT", "ARE", "TEN", "DOG", "EAR", "OLD", "ICE", "ACE", "TIE"]
    wl = WordList.from_pairs((w, 50.0) for w in words)
    monkeypatch.setattr(engine, "get_wordlist", lambda: wl)
    monkeypatch.setattr(engine, "get_clue_db", lambda: None)  # word-list only here


def test_solve_open_grid_no_slots() -> None:
    # Manual entry sends just the grid (no slots); the backend derives them.
    puzzle = {
        "width": 3,
        "height": 3,
        "cells": [["", "", ""], ["", "", ""], ["", "", ""]],
    }
    res = client.post("/solve", json=puzzle)
    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "solved"
    for row in data["filled"]:
        for cell in row:
            assert cell not in (None, "")  # fully filled, no blocks here
    assert len(data["answers"]) == 6
    assert all(a["answer"] for a in data["answers"])
