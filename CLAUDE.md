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

## Known limitation

The CSP returns the *first* globally consistent fill, not the one that maximizes
clue agreement — an entry completed via crossings ignores its own clue (e.g. a
"Golf goal" entry may fill PAM instead of PAR). See ARCHITECTURE §11. Roadmap and
status: ARCHITECTURE §9 (steps 1–3 done: engine, clue DB, Crosshare adapter).
