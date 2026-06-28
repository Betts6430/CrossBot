# shared/

The **data contract** between the extension and the backend.

[`puzzle.schema.json`](puzzle.schema.json) is the single source of truth for how
a crossword is represented. Both sides mirror it:

- the extension in [`extension/lib/model`](../extension/lib/model) (TypeScript types)
- the backend in [`backend/app/models.py`](../backend/app/models.py) (Pydantic models)

If you change the schema, update **both** mirrors. The two key shapes are:

- **`Puzzle`** — a normalized crossword (grid + slots + clues). Produced by site
  adapters, the manual-entry editor, and (later) `.puz` / `.ipuz` import.
- **`SolveResult`** — what `POST /solve` returns: the filled grid plus per-slot
  answers and confidence.

See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) section 4 for the rationale.
