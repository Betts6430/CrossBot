# CrossBot backend

A small [FastAPI](https://fastapi.tiangolo.com) server that runs **locally** and
solves crosswords. It exposes `POST /solve` (takes a `Puzzle`, returns a
`SolveResult`) and `GET /health`.

## Run

```bash
# with uv (recommended)
uv sync
uv run uvicorn app.main:app --reload      # http://localhost:8000

# or with pip
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Interactive API docs: <http://localhost:8000/docs>.

## Test

```bash
uv run pytest      # or: pytest
```

## Layout

```
app/
  main.py            FastAPI app + /health
  api/routes.py      POST /solve
  models.py          Pydantic mirror of shared/puzzle.schema.json
  solver/
    engine.py        orchestrates the solve
    candidates.py    per-slot candidates (DB lookup + word list)
    csp.py           constraint-satisfaction grid fill
    scoring.py       candidate ranking
    llm.py           optional booster (OFF by default)
  data/loaders.py    load word list + clue database
data/                datasets (gitignored; fetched/built locally)
tests/
```

The solving logic is not implemented yet — see
[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) section 9 for the build order.
