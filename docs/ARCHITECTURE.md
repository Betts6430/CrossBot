# CrossBot — Architecture & Codebase Decisions

**Status:** Draft / pre-implementation
**Last updated:** 2026-06-28

CrossBot is a tool that **solves and autocompletes crosswords directly in the
browser**. You open a puzzle on a supported site (or type one in by hand), and
CrossBot fills the grid for you.

This document records the framework and technology decisions made before coding
started, and why we made them. It's the source of truth for how the project is
put together.

---

## 1. Decisions at a glance

| Question | Decision |
| --- | --- |
| Where it runs | **Browser extension + a local backend** (the backend runs on your own machine at `localhost`, so there is no hosting cost) |
| How it gets the puzzle | **Auto-read from supported sites** (DOM scraping via per-site adapters) **+ manual entry** as the always-works fallback |
| How answers are generated | **Hybrid, free, offline:** clue-answer database lookup + word-list constraint solver. An LLM "booster" is an *optional, off-by-default* plug-in |
| Audience & automation | **Personal use, full auto-solve** — no accounts, no auth, no scaling concerns |

The guiding constraint: **the default experience must be free** (no paid APIs, no
paid hosting). Everything below follows from that.

---

## 2. Why this shape

### Platform: extension + local backend
- A **browser extension** is the only option that can read the puzzle straight
  off the page and write answers back *in place*, which is the experience we
  want ("solve while I'm looking at it").
- A **local backend** (a small Python server running on your machine) does the
  heavy lifting: holding large datasets, fast fuzzy text search, and the
  constraint solver. Because it runs at `localhost`, it costs nothing to host.
- This keeps the extension thin (UI + page scraping + overlay) and puts the
  smart parts somewhere easy to grow and test in Python.

> **Alternative considered:** put everything in the extension and drop the
> backend. Viable later, but bundling a multi-megabyte clue database into an
> extension and running the solver inside a Manifest V3 service worker is
> awkward. We keep the door open (the puzzle model and API are designed so the
> solver *could* be ported to TypeScript/WASM later), but start with a backend.

### Solver: hybrid, free, LLM optional
A pure-LLM solver was rejected for two reasons: hosted LLM APIs cost money per
puzzle, and an LLM on its own is bad at the thing that matters most — making
every crossing letter agree. The free hybrid covers both novel and repeated
clues:

1. **Clue-answer database lookup.** Crossword clues repeat heavily across years
   of published puzzles. We load a free corpus of `clue → answer` pairs into a
   local database and do exact + fuzzy matching to produce ranked candidate
   answers per slot. This alone solves a large fraction of clues.
2. **Word-list + constraint solver (CSP).** For slots the database doesn't
   know, a scored crossword word list supplies length-filtered candidates. The
   grid is then treated as a **constraint-satisfaction problem** — each slot is
   a variable, each crossing cell is a constraint — and solved with constraint
   propagation + weighted backtracking to produce a globally consistent fill.
   This is the actual "autocomplete the grid" engine.
3. **Optional LLM booster (off by default).** A pluggable hook that answers
   leftover novel clues *only if you enable it*. To stay free it points at a
   **local model via [Ollama](https://ollama.com)** or your own API key. The
   default experience needs none of this.

---

## 3. High-level architecture

```
┌────────────────────────── Browser ──────────────────────────┐
│  Crossword site (Guardian, LA Times, …)                      │
│     ▲ reads grid+clues from page        ▼ writes answers     │
│  ┌───────────── CrossBot extension (MV3, TS) ─────────────┐  │
│  │  content script: site adapters + grid overlay          │  │
│  │  popup / options: manual entry, "Solve", settings      │  │
│  │  background: message routing                            │  │
│  └───────────────────────┬────────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────────┘
                           │  Puzzle JSON  ▲  SolveResult JSON
                           ▼               │
        ┌──────────── Local backend (Python, FastAPI) ──────────┐
        │  POST /solve                                          │
        │    1. candidates: DB lookup + scored word list        │
        │    2. CSP solve: constraint propagation + backtracking│
        │    3. (optional) LLM booster for unresolved slots     │
        │  data: clues.sqlite (FTS), wordlist.txt               │
        └────────────────────────────────────────────────────────┘
```

The **Puzzle JSON model** (see §4) is the contract between the two halves. It is
the single most important interface in the project: as long as both sides agree
on it, the extension and backend can evolve independently.

---

## 4. The puzzle data model (the contract)

A normalized JSON representation, loosely aligned with the
[`.ipuz`](http://www.ipuz.org/) format so that file import (`.puz` / `.ipuz`)
can be added later without changing the model. The canonical schema lives in
[`shared/puzzle.schema.json`](../shared/puzzle.schema.json).

Key ideas:

- **`cells`** is a 2D grid. Each cell is either a **block** (`null`), an **empty
  fillable cell** (`""`), or a **given letter** (e.g. `"A"`).
- **`slots`** is the list of answer positions. Each slot knows its number,
  direction (`across` / `down`), ordered cell coordinates, length, and clue
  text. The solver fills in each slot's `answer`.
- A **`SolveResult`** returns the filled grid plus per-slot answers and a
  confidence score, and an overall `status` (`solved` / `partial` / `failed`).

This model is intentionally UI-agnostic — site adapters, the manual-entry
editor, and (later) file importers all produce the *same* `Puzzle`, and the
overlay consumes the *same* `SolveResult`.

---

## 5. Components

### Extension (`extension/`)
- **`entrypoints/content`** — runs on supported puzzle pages. Uses a **site
  adapter** to read the grid + clues into a `Puzzle`, sends it to the backend,
  then renders the returned answers as an **overlay** (drawn in a Shadow DOM so
  the host site's CSS can't interfere).
- **`entrypoints/popup`** — the toolbar UI: a **manual grid editor**, the
  **Solve** button, and settings (backend URL, optional LLM toggle).
- **`entrypoints/background`** — the MV3 service worker; routes messages between
  popup, content scripts, and the backend.
- **`lib/model`** — TypeScript types mirroring the puzzle schema.
- **`lib/api`** — the backend client (`/solve`, `/health`).
- **`lib/adapters`** — an `Adapter` interface plus one implementation per
  supported site. Adding a site = adding one adapter, nothing else.

### Backend (`backend/`)
- **`app/api`** — FastAPI routes (`POST /solve`, `GET /health`).
- **`app/models.py`** — Pydantic models mirroring the puzzle schema.
- **`app/solver`** — the engine:
  - `candidates.py` — per-slot candidate generation (DB lookup + word list).
  - `csp.py` — constraint-satisfaction fill (propagation + weighted backtracking).
  - `scoring.py` — candidate scoring / ranking.
  - `llm.py` — the optional, off-by-default LLM booster (`Gap`, `OllamaClient`,
    `build_prompt`, `parse_answers`, `boost`); enabled via `CROSSBOT_LLM=ollama`
    (config in `app/config.py`). Fed only unresolved slots with their crossing-
    letter patterns; returns validated, scored candidates. **Wired into
    `engine.solve_puzzle`**: after the CSP solve, leftover clued slots become
    `Gap`s, get boosted, are injected via `CandidateProvider.add_candidates`, and
    the grid is re-solved — repeated for a few rounds (stopping early on no
    progress) so each fill tightens the patterns the model sees. The model's
    answers improve the fill but are **painted only where corroborated** by
    confident (clue-DB/given) crossings, so a free-floating guess never shows.
  - `engine.py` — orchestrates the above.
- **`app/data`** — loaders for the word list and the clue database.
- **`data/`** — the actual datasets (word list, `clues.sqlite`). **Not committed**
  (see §7); fetched/built locally.

### Shared (`shared/`)
- **`puzzle.schema.json`** — the JSON Schema that both sides conform to. The
  single source of truth for the data contract.

---

## 6. Technology stack

| Area | Choice | Why |
| --- | --- | --- |
| Extension framework | **[WXT](https://wxt.dev)** (Vite-based) | Modern MV3 tooling, HMR, builds Chrome **and** Firefox from one codebase |
| Extension language | **TypeScript** | Type safety against the shared puzzle model |
| Extension UI | **React** in a **Shadow DOM** | Familiar; Shadow DOM isolates the overlay from host-page styles |
| Manifest | **Manifest V3** | Required by current Chrome; supported by WXT |
| Backend language | **Python 3.11+** | Best ecosystem for text data + solver work |
| Backend framework | **FastAPI + Uvicorn** | Small, fast, typed; trivial JSON API |
| Validation | **Pydantic v2** | Mirrors the puzzle schema, validates requests |
| Clue database | **SQLite + FTS5** | Zero-setup, fast full-text/fuzzy clue search, ships as one file |
| Fuzzy matching | **rapidfuzz** | Fast candidate ranking |
| Tests | **pytest** (backend), **Vitest + Playwright** (extension) | Solver accuracy on a puzzle corpus; adapter scraping against saved HTML fixtures |
| Env / tasks | **uv** (Python), **npm** (extension) | Fast, reproducible installs |

---

## 7. Data sources & legal notes

- **Word lists** — Peter Broda's crossword word list (free for personal use,
  scored by quality) or public-domain alternatives (ENABLE/SOWPODS).
- **Clue corpus** — the [xd corpus](https://xd.saul.pw/data) (Saul Pwanson /
  century-arcade), ~8M clue/answer usages, built into `clues.sqlite`. Fetched
  locally and gitignored; not redistributed (no explicit license — it's derived
  from published puzzles, used here for personal/local solving only).
- **Datasets are not committed to git.** They can be large and have their own
  licenses; a setup script fetches/builds them locally into `backend/data/`.
- **Scraping is per-site and personal-use only.** We do not redistribute scraped
  data. **NYT is intentionally not a first target** — it is subscription-gated
  and restricts automated access. Better starting targets are free puzzles or
  sites built on the common **Amuse Labs "PuzzleMe"** embed (one adapter can
  cover many newspapers). Respect each site's Terms of Service.

---

## 8. Repository layout

```
CrossBot/
├── docs/
│   └── ARCHITECTURE.md          # this file
├── shared/
│   ├── puzzle.schema.json       # the data contract (single source of truth)
│   └── README.md
├── extension/                   # WXT + TypeScript + React (MV3)
│   ├── entrypoints/
│   │   ├── background.ts
│   │   ├── content.ts
│   │   └── popup/
│   ├── lib/
│   │   ├── model/               # puzzle types
│   │   ├── api/                 # backend client
│   │   └── adapters/            # one per supported site
│   ├── wxt.config.ts
│   ├── tsconfig.json
│   └── package.json
├── backend/                     # FastAPI solver
│   ├── app/
│   │   ├── api/
│   │   ├── solver/
│   │   ├── data/
│   │   ├── models.py
│   │   └── main.py
│   ├── data/                    # datasets (gitignored)
│   ├── tests/
│   └── pyproject.toml
├── .gitignore
└── README.md
```

---

## 9. Build order (roadmap)

The plan is to prove the engine first, then layer on automation.

1. ✅ **Engine MVP** — puzzle model + manual entry + "fill grid" using only the
   word list and CSP solver (no scraping, no database). Proves the core fill
   works end-to-end. *Done: `backend/app/solver/` (grid derivation, word-list
   index, backtracking CSP) and the popup grid editor in `extension/`.*
2. ✅ **Clue database** — `clue → answer` lookup → large accuracy jump. *Done:
   `backend/app/data/clue_db.py` (SQLite: exact `clue_answer` table + `answers`
   vocab + FTS5 fuzzy) built from the xd corpus by `scripts/fetch_clues.py`;
   `CandidateProvider` feeds clue answers into the CSP, preferred over plain
   word-list fill.*
3. ✅ **First site adapter + overlay** — auto-read one supported site, solve,
   fill in place. *Done: Crosshare. `extension/lib/adapters/crosshare.ts` reads
   the puzzle from `__NEXT_DATA__`; the content script injects a Solve button and
   messages the background worker (which fetches the backend — a content-script
   fetch would hit the page CSP); `lib/overlay.ts` paints answers in a fixed
   layer anchored to each cell's rect. Verified live in a real browser.*
4. **Polish & breadth** — per-clue fill / single-letter reveal, more site
   adapters, optional Ollama booster (*in progress*: client/prompt/parse, iterative
   engine integration, confidence calibration, and the per-solve toggle landed — LLM
   answers feed the CSP but only paint where corroborated by confident crossings;
   `POST /solve?boost=` opts in/out per request, `/health` advertises whether a
   booster is configured, and the extension surfaces both as a "use AI booster"
   checkbox; live validation against a real Ollama box next), then `.puz` / `.ipuz`
   file import.

---

## 10. Non-goals (for now)

- No user accounts, login, or cloud sync (personal, single-user).
- No paid APIs or paid hosting in the default path.
- No NYT scraping as a first target (ToS + paywall).
- Not packaged as a public product yet — that's a later, separate decision.

## 11. Open questions / future decisions

- **Browser scope:** Chrome-first, with Firefox added via WXT when convenient.
- **Backend distribution:** start as a `uv`-run local server; later, optionally
  bundle to a single one-click binary (e.g. PyInstaller) so there's no terminal
  step.
- **Possible backend-free mode:** port the solver to TS/WASM if we ever want a
  zero-install, extension-only build.
- **Solver quality (resolved):** the CSP no longer returns the *first* consistent
  fill. `csp.py` is a score-maximizing branch-and-bound over candidates scored by
  `max(clue confidence, quality prior)`, with **maintained arc consistency** (cell
  letter-domains propagate on each assignment) so dense 15×15 grids fill in
  hundreds of nodes instead of thrashing. It keeps the highest-*total*-score
  complete fill, so an entry completed by crossings still prefers its own clue
  answer (e.g. "Golf goal" → PAR, verified on a real Crosshare mini).
- **Full-grid accuracy is signal-limited.** Minis solve ~100%, but a 15×15
  themeless lands ~15–20% if forced to complete: most of its clues have no corpus
  match, so the only signal is crossings + a word-frequency prior. This is a
  *knowledge* gap (what the optional LLM booster, §9 step 4, is for), not a search
  one — proven by the search still failing to complete a 15×15 even when the true
  answers are injected into the vocabulary. Because a mostly-wrong complete grid is
  worse than useless as an overlay, `engine.py` **paints only what it's confident
  about**: a clued cell shows only when a covering slot clears
  `CONFIDENCE_THRESHOLD` (a clue match; a quality-only guess ≤0.55 does not), so on
  a hard grid we surface the answers we know (the strong clue answers, placed as
  consistent anchors) and leave the rest blank. Unclued manual-entry grids have no
  clue to doubt, so they're filled in full.
- **Solve latency on big grids:** clue-DB lookups are now parallelized
  (`ClueDB.lookup_many`: a thread pool with per-thread read-only connections,
  primed once via `CandidateProvider.prime_clues`) — a 70-clue grid dropped from
  ~12 s to ~2.4 s (~5×). The remaining ~8 s on a hard 15×15 is the solver's own
  time budget (it can't complete, so it searches to the limit); tightening that is
  the next lever.
