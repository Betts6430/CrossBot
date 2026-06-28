"""Load datasets from backend/data/ (gitignored; fetched/built locally).

  - word list: scored crossword entries, used as candidate priors.
  - clue database: SQLite (+ FTS5) of historical clue -> answer pairs.

See docs/ARCHITECTURE.md section 7 for sources and licensing. Not implemented
yet.
"""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
WORDLIST_PATH = DATA_DIR / "wordlist.txt"
CLUES_DB_PATH = DATA_DIR / "clues.sqlite"


def load_wordlist() -> dict[str, float]:
    """Return a mapping of UPPERCASE entry -> quality score."""
    raise NotImplementedError


def connect_clue_db() -> object:
    """Open a connection to the clue-answer SQLite database."""
    raise NotImplementedError
