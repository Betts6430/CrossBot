"""Download a free word list into backend/data/wordlist.txt.

Usage (from the backend/ directory):
    python scripts/fetch_wordlist.py

Default source is ENABLE1 (public domain) — a solid general fill list. For a
crossword-tuned, CC0 list with quality scores, see
https://www.spreadthewordlist.com and point SOURCES at its .dict file (the
loader already understands the "WORD;score" format).
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEST = DATA_DIR / "wordlist.txt"

SOURCES = [
    "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt",
]


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for url in SOURCES:
        try:
            print(f"Downloading {url} ...")
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
            DEST.write_bytes(data)
            lines = DEST.read_text(encoding="utf-8", errors="ignore").count("\n")
            print(f"Wrote {DEST} ({lines:,} lines)")
            return 0
        except Exception as exc:  # noqa: BLE001 - report and try next source
            print(f"  failed: {exc}", file=sys.stderr)
    print("All sources failed.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
