"""Download the xd clue corpus and build backend/data/clues.sqlite.

Usage (from the backend/ directory):
    python scripts/fetch_clues.py                 # download + build
    python scripts/fetch_clues.py --zip path.zip  # build from a local zip
    python scripts/fetch_clues.py --limit 100000   # quick partial build (testing)

Source: the xd corpus (https://xd.saul.pw/data), ~6M clue/answer usages. The
data is fetched locally and is gitignored -- it is not redistributed. Answers
that aren't plain A-Z words (variety/cryptic entries like "1UP") are dropped.
See docs/ARCHITECTURE.md section 7.
"""

from __future__ import annotations

import argparse
import io
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterator

from app.data.clue_db import build_clue_db

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_URL = "https://xd.saul.pw/xd-clues.zip"
CLUES_MEMBER = "xd/clues.tsv"


def _iter_usages(zip_path: Path, limit: int | None) -> Iterator[tuple[str, str]]:
    """Yield (answer, clue) from xd/clues.tsv inside the zip."""
    with zipfile.ZipFile(zip_path) as zf, zf.open(CLUES_MEMBER) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8", errors="ignore")
        header = next(text, "")  # skip "pubid\tyear\tanswer\tclue"
        if not header.lower().startswith("pubid"):
            # Not the header we expected; treat it as data.
            parts = header.rstrip("\n").split("\t", 3)
            if len(parts) == 4:
                yield parts[2], parts[3]
        for i, line in enumerate(text):
            if limit is not None and i >= limit:
                break
            parts = line.rstrip("\n").split("\t", 3)
            if len(parts) == 4:
                yield parts[2], parts[3]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", type=Path, help="Use a local xd-clues.zip instead of downloading")
    ap.add_argument("--db", type=Path, default=DATA_DIR / "clues.sqlite")
    ap.add_argument("--limit", type=int, help="Only read the first N rows (testing)")
    ap.add_argument("--keep-zip", action="store_true", help="Keep the downloaded zip")
    args = ap.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = args.zip
    downloaded = False
    if zip_path is None:
        zip_path = DATA_DIR / "xd-clues.zip"
        if not zip_path.exists():
            print(f"Downloading {DEFAULT_URL} ...")
            try:
                urllib.request.urlretrieve(DEFAULT_URL, zip_path)
                downloaded = True
            except Exception as exc:  # noqa: BLE001
                print(f"  download failed: {exc}", file=sys.stderr)
                return 1
    if not zip_path.exists():
        print(f"Zip not found: {zip_path}", file=sys.stderr)
        return 1

    print(f"Building {args.db} from {zip_path} ...")
    kept = build_clue_db(_iter_usages(zip_path, args.limit), args.db)
    size_mb = args.db.stat().st_size / 1e6
    print(f"Done: kept {kept:,} usages -> {args.db} ({size_mb:.0f} MB)")

    if downloaded and not args.keep_zip:
        zip_path.unlink(missing_ok=True)
        print("Removed downloaded zip (use --keep-zip to keep it).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
