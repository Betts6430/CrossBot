# CLAUDE.md

Guidance for working in this repo. Full design rationale lives in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — read it before non-trivial changes.

## What this is

CrossBot solves/autocompletes crosswords in the browser. Free, personal, local.

- **`backend/`** — FastAPI solver (Python 3.11+). Does the actual solving.
- **`extension/`** — browser extension (Manifest V3, WXT + TypeScript + React).
- **`shared/puzzle.schema.json`** — the data contract between the two halves.

Solver pipeline: a clue-answer database (xd corpus) + a word-list constraint
solver (`backend/app/solver/`), combined by `CandidateProvider`. An LLM booster
is optional and off by default. The default path stays free (no paid APIs/hosting).

## Architecture quick map

- Request/response model: `backend/app/models.py` ⇄ `extension/lib/model/puzzle.ts`
  ⇄ `shared/puzzle.schema.json`. **Keep all three in sync** when the shape changes.
- Backend: `app/main.py` (`/health`, `POST /solve`) → `app/solver/engine.py`
  (orchestrates) → `candidates.py` (CandidateProvider) + `csp.py` (backtracking
  fill) + `data/{clue_db,loaders,wordlist?}`. Word list/index in
  `app/solver/wordlist.py`; clue DB build+query in `app/data/clue_db.py`.
- Extension: `entrypoints/{popup,content,background}`; `lib/adapters/*` (one per
  site, e.g. `crosshare.ts`), `lib/overlay.ts` (paints answers), `lib/api` +
  `lib/messaging`. The content script messages the **background** worker to fetch
  the backend (a content-script fetch would hit the host page's CSP).

## Commands

Backend (run from repo root; see Local environment for the exact prefixes):
- Run server: `uvicorn app.main:app --port 8000` (cwd `backend/`, or module path)
- Tests: `pytest backend/tests`
- One-time data: `python backend/scripts/fetch_wordlist.py` and
  `python backend/scripts/fetch_clues.py` (builds `backend/data/clues.sqlite`, ~500 MB)

Extension (from `extension/`):
- `npm install` → `npm run dev` (Chrome) / `npm run build` / `npm run compile`
  (tsc) / `npm test` (Vitest).

## Local environment (THIS WSL box — important)

This machine has quirks; commands fail without these. Copy-paste forms that work:

- **ROS leak**: ROS Jazzy is sourced in the shell, so `PYTHONPATH` includes
  `/opt/ros/...` and breaks pytest plugin autoload. Always prefix Python with
  `env -u PYTHONPATH`, and pytest also with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.
- **Node** is a standalone install at `~/.local/node/bin`, not on PATH:
  `export PATH="$HOME/.local/node/bin:$PATH"` before any npm command.
- **Backend venv** lives at `backend/.venv` (pip was bootstrapped via get-pip.py
  because this box's venv lacks ensurepip; recreate with
  `python3 -m venv --without-pip backend/.venv` + get-pip.py if needed).

```bash
# backend tests
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 backend/.venv/bin/python -m pytest backend/tests -q
# run backend
env -u PYTHONPATH backend/.venv/bin/python -m uvicorn app.main:app --port 8000
# extension test/build
export PATH="$HOME/.local/node/bin:$PATH" && npm test --prefix extension
```

## Conventions & notes

- **Datasets are gitignored and never committed/redistributed** (`backend/data/`):
  word list (ENABLE) and `clues.sqlite` (xd corpus). Fetched by the scripts above.
- Commit at milestones; push to `origin` (the `github-personal` SSH alias →
  `Betts6430/CrossBot`; the default `github.com` key is a different account).
- Tests: backend = pytest; extension = Vitest (jsdom). Real-browser checks use
  Playwright headful (works via WSLg) — installed transiently, not a committed dep.

## Solver behaviour & limitation

`csp.py` is a score-maximizing branch-and-bound with **maintained arc consistency**
(cell letter-domains propagate per assignment), so it prefers clue answers (e.g.
"Golf goal" → PAR) and fills dense 15×15 grids in hundreds of nodes. It keeps the
highest-total-score complete fill, not just the first consistent one.

Accuracy on a full 15×15 is **signal-limited** (~15–20%): most themeless clues have
no corpus match, so there's little to solve from. So `engine.py` **paints only
confident cells** — a clued cell shows only when a covering slot clears
`CONFIDENCE_THRESHOLD` (a clue match), surfacing what we know and leaving the rest
blank; unclued manual-entry grids fill fully. Minis solve ~100%. Clue-DB lookups
are parallelized (`ClueDB.lookup_many` + `CandidateProvider.prime_clues`: per-thread
read-only connections), ~5× faster on a 70-clue grid; the rest of a hard 15×15's
time is the solver's own search budget. See ARCHITECTURE §11. Roadmap: §9 (steps
1–3 done; step 4 = LLM booster + breadth).
