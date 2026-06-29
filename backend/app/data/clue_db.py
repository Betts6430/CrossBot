"""The clue-answer database: build it, and query it.

Backed by SQLite. From a stream of (answer, clue) usages we build:

  - ``clue_answer(nclue, answer, n)`` -- distinct normalized-clue -> answer pairs
    with usage counts, indexed on ``nclue`` for fast exact lookup.
  - ``answers(answer, total)`` -- the answer vocabulary with overall frequency,
    used as a fill-validity check and a prior.
  - ``clue_fts`` -- an FTS5 index over ``nclue`` for fuzzy (token-overlap)
    lookup when the exact clue isn't present.

``normalize_clue`` MUST be identical at build time and query time, so it lives
here and both sides import it.
"""

from __future__ import annotations

import re
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Iterable

_NON_ALNUM = re.compile(r"[^a-z0-9\s]+")
_WS = re.compile(r"\s+")

# Answers we keep as crossword fill: A-Z only, sensible length.
MIN_ANSWER_LEN = 2
MAX_ANSWER_LEN = 24
# Cap stored clue length so a few pathological paragraph-clues don't bloat the index.
_MAX_NCLUE = 200


def normalize_clue(clue: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace. Used for exact match."""
    s = _NON_ALNUM.sub(" ", clue.strip().lower())
    return _WS.sub(" ", s).strip()[:_MAX_NCLUE]


def clean_answer(answer: str) -> str | None:
    """Uppercase A-Z answer, or None if it isn't usable as fill."""
    a = answer.strip().upper()
    if a.isalpha() and MIN_ANSWER_LEN <= len(a) <= MAX_ANSWER_LEN:
        return a
    return None


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #


def build_clue_db(usages: Iterable[tuple[str, str]], db_path: Path | str) -> int:
    """Build clues.sqlite from (answer, clue) usages. Returns rows kept."""
    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        # journal/sync off for a fast throwaway build (we just rebuild on
        # failure); temp_store left on disk so the 6M-row GROUP BY can't OOM.
        conn.executescript(
            """
            PRAGMA journal_mode = OFF;
            PRAGMA synchronous = OFF;
            CREATE TABLE usage (nclue TEXT NOT NULL, answer TEXT NOT NULL);
            """
        )

        kept = 0
        batch: list[tuple[str, str]] = []
        for answer, clue in usages:
            a = clean_answer(answer)
            if a is None:
                continue
            nclue = normalize_clue(clue)
            if not nclue:
                continue
            batch.append((nclue, a))
            if len(batch) >= 50_000:
                conn.executemany("INSERT INTO usage VALUES (?, ?)", batch)
                kept += len(batch)
                batch.clear()
        if batch:
            conn.executemany("INSERT INTO usage VALUES (?, ?)", batch)
            kept += len(batch)
        conn.commit()

        conn.executescript(
            """
            CREATE TABLE clue_answer AS
                SELECT nclue, answer, COUNT(*) AS n
                FROM usage GROUP BY nclue, answer;
            CREATE INDEX idx_clue_answer_nclue ON clue_answer(nclue);

            CREATE TABLE answers AS
                SELECT answer, SUM(n) AS total
                FROM clue_answer GROUP BY answer;
            CREATE UNIQUE INDEX idx_answers_answer ON answers(answer);

            CREATE VIRTUAL TABLE clue_fts USING fts5(
                nclue, answer UNINDEXED, n UNINDEXED, tokenize = 'unicode61'
            );
            INSERT INTO clue_fts (nclue, answer, n)
                SELECT nclue, answer, n FROM clue_answer;

            DROP TABLE usage;
            """
        )
        conn.commit()
        conn.execute("VACUUM")
        conn.commit()
        return kept
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# Query
# --------------------------------------------------------------------------- #


def _fts_match(nclue: str) -> str:
    """Build a forgiving FTS5 query (OR of quoted tokens) from a clue."""
    tokens = [t for t in nclue.split() if len(t) >= 2][:12]
    return " OR ".join(f'"{t}"' for t in tokens)


def _lookup(conn: sqlite3.Connection, clue: str, limit: int) -> list[tuple[str, float]]:
    """The query itself, on a given connection: exact matches beat fuzzy."""
    nclue = normalize_clue(clue)
    if not nclue:
        return []
    scores: dict[str, float] = {}

    # Exact normalized-clue match, most-used answer first.
    exact = conn.execute(
        "SELECT answer FROM clue_answer WHERE nclue = ? ORDER BY n DESC LIMIT ?",
        (nclue, limit),
    ).fetchall()
    for i, (answer,) in enumerate(exact):
        scores[answer] = max(scores.get(answer, 0.0), 0.99 - 0.002 * i)

    # Fuzzy token-overlap via FTS, ranked by bm25 (SQLite: lower = better).
    match = _fts_match(nclue)
    if match:
        try:
            fuzzy = conn.execute(
                "SELECT answer FROM clue_fts WHERE clue_fts MATCH ? "
                "ORDER BY bm25(clue_fts) LIMIT ?",
                (match, limit),
            ).fetchall()
            for i, (answer,) in enumerate(fuzzy):
                scores[answer] = max(scores.get(answer, 0.0), 0.6 - 0.004 * i)
        except sqlite3.OperationalError:
            pass

    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


class ClueDB:
    """Read-only query interface over clues.sqlite."""

    def __init__(self, conn: sqlite3.Connection, path: Path | str | None = None) -> None:
        self.conn = conn
        self.path = str(path) if path is not None else None
        self._answer_cache: dict[str, bool] = {}
        self._freq: dict[str, int] | None = None

    @classmethod
    def open(cls, path: Path | str) -> "ClueDB":
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        return cls(conn, path)

    def lookup(self, clue: str, limit: int = 40) -> list[tuple[str, float]]:
        """Ranked (ANSWER, confidence) for a clue: exact matches beat fuzzy."""
        return _lookup(self.conn, clue, limit)

    def lookup_many(
        self, clues: Iterable[str], limit: int = 40, max_workers: int = 8
    ) -> dict[str, list[tuple[str, float]]]:
        """Look up several clues at once, in parallel.

        The fuzzy FTS query dominates a solve's latency (~tens of ms each over the
        ~500 MB index), and SQLite releases the GIL during a query, so running them
        on a small pool of threads -- each with its own read-only connection --
        gives a real speedup. Falls back to serial when the DB wasn't opened from a
        path (e.g. an in-memory test handle) or there's nothing to gain.
        """
        uniq = list(dict.fromkeys(clues))
        if self.path is None or len(uniq) <= 1:
            return {c: _lookup(self.conn, c, limit) for c in uniq}

        local = threading.local()
        opened: list[sqlite3.Connection] = []
        opened_lock = threading.Lock()

        def conn_for_thread() -> sqlite3.Connection:
            conn = getattr(local, "conn", None)
            if conn is None:
                conn = sqlite3.connect(
                    f"file:{self.path}?mode=ro", uri=True, check_same_thread=False
                )
                local.conn = conn
                with opened_lock:
                    opened.append(conn)
            return conn

        def task(clue: str) -> tuple[str, list[tuple[str, float]]]:
            return clue, _lookup(conn_for_thread(), clue, limit)

        try:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(uniq))) as pool:
                return dict(pool.map(task, uniq))
        finally:
            for conn in opened:
                conn.close()

    def frequencies(self) -> dict[str, int]:
        """All answers -> how often they appear as a fill (a quality prior).

        Loaded once into memory (~hundreds of thousands of entries).
        """
        if self._freq is None:
            self._freq = dict(self.conn.execute("SELECT answer, total FROM answers"))
        return self._freq

    def is_known_answer(self, word: str) -> bool:
        cached = self._answer_cache.get(word)
        if cached is None:
            row = self.conn.execute(
                "SELECT 1 FROM answers WHERE answer = ? LIMIT 1", (word,)
            ).fetchone()
            cached = row is not None
            self._answer_cache[word] = cached
        return cached

    def close(self) -> None:
        self.conn.close()
