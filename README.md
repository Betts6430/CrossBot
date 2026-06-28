# CrossBot

A free, personal tool that **solves and autocompletes crosswords in your
browser**. Open a puzzle on a supported site (or type one in by hand), hit
**Solve**, and CrossBot fills the grid.

It has two parts:

- **`extension/`** — a browser extension (Manifest V3, built with
  [WXT](https://wxt.dev)) that reads the puzzle off the page (or via manual
  entry) and overlays the answers.
- **`backend/`** — a small Python ([FastAPI](https://fastapi.tiangolo.com))
  server that runs **locally on your machine** and does the actual solving. No
  paid APIs, no hosting — it stays free.

> **How it solves:** a clue-answer database handles clues that have appeared
> before, a scored word list + constraint solver fills the rest while keeping
> every crossing letter consistent, and an **optional, off-by-default** LLM
> booster (local via Ollama, or your own key) can tackle leftover novel clues.

See **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for the full design and the
reasoning behind every decision.

---

## Status

**Auto-solves crosswords on a real site.** On a [Crosshare](https://crosshare.org)
puzzle page, the extension shows a "Solve with CrossBot" button that reads the
grid + clues off the page, solves it via the backend (clue-answer database +
word-list constraint solver), and overlays the answers in place. Manual grid
entry also works in the popup. Not yet built: more site adapters (Amuse/PuzzleMe
family, NYT) and the optional LLM booster. See the roadmap in the architecture doc.

## Project layout

```
extension/   browser extension (WXT + TypeScript + React, MV3)
backend/     FastAPI solver (Python 3.11+)
shared/      puzzle.schema.json — the data contract both sides share
docs/        architecture & decisions
```

## Quick start (once dependencies are added)

### Backend
```bash
cd backend
uv sync                 # or: pip install -e ".[dev]"
python scripts/fetch_wordlist.py         # one-time: downloads data/wordlist.txt
python scripts/fetch_clues.py            # one-time: builds data/clues.sqlite (~500 MB)
uv run uvicorn app.main:app --reload     # serves http://localhost:8000
```

### Extension
```bash
cd extension
npm install
npm run dev             # launches a dev browser with the extension loaded
```

The extension talks to the backend at `http://localhost:8000` by default
(configurable in the popup settings).
