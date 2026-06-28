"""Load datasets from backend/data/ (gitignored; fetched/built locally).

  - word list: scored crossword entries, used as candidate priors.
  - clue database: SQLite (+ FTS5) of historical clue -> answer pairs (later).

See docs/ARCHITECTURE.md section 7 for sources and licensing.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable, Iterator

from app.solver.wordlist import WordList

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
WORDLIST_PATH = DATA_DIR / "wordlist.txt"
CLUES_DB_PATH = DATA_DIR / "clues.sqlite"

# Separators seen in common word-list formats: "WORD;score", "WORD\tscore", …
_SEPARATORS = (";", "\t", ",")
DEFAULT_WORD_SCORE = 50.0


def parse_wordlist_lines(lines: Iterable[str]) -> Iterator[tuple[str, float]]:
    """Yield (word, score) from word-list lines. Plain words default to 50."""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        for sep in _SEPARATORS:
            if sep in line:
                word, _, rest = line.partition(sep)
                try:
                    yield word, float(rest)
                except ValueError:
                    yield word, DEFAULT_WORD_SCORE
                break
        else:
            yield line, DEFAULT_WORD_SCORE


def load_wordlist(path: Path | None = None) -> WordList:
    path = path or WORDLIST_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Word list not found at {path}. "
            "Fetch one with: python scripts/fetch_wordlist.py"
        )
    with path.open(encoding="utf-8", errors="ignore") as f:
        return WordList.from_pairs(parse_wordlist_lines(f))


@lru_cache(maxsize=1)
def get_wordlist() -> WordList:
    """Load and cache the word list (built once per process)."""
    return load_wordlist()


@lru_cache(maxsize=1)
def get_clue_db() -> "ClueDB | None":
    """Open and cache the clue database, or None if it hasn't been built yet."""
    if not CLUES_DB_PATH.exists():
        return None
    from app.data.clue_db import ClueDB

    return ClueDB.open(CLUES_DB_PATH)
