"""Top-level orchestration of a solve.

Pipeline (see docs/ARCHITECTURE.md):
    1. derive entries from the grid (or use those the puzzle carries, with clues)
    2. CSP fill using a CandidateProvider = clue database + word list
    3. (optional, off by default) LLM booster: ask a local model about still-
       unresolved slots, inject its answers, and re-solve -- repeat a few rounds so
       each fill tightens the crossing letters the model sees.
"""

from __future__ import annotations

from app.config import llm_config
from app.data.loaders import get_clue_db, get_wordlist
from app.models import Puzzle, SlotAnswer, SolveResult
from app.solver.candidates import CandidateProvider
from app.solver.csp import Solver
from app.solver.grid import Coord, Entry, derive_entries
from app.solver.llm import Gap, boost, get_llm_client

# For a *clued* slot, only paint a cell when some covering slot scores at least
# this. A clue match (exact ~0.9-0.99, top fuzzy ~0.6) clears it; a fill chosen
# only from the quality prior (<=0.55) does not. So on a hard clued grid we show
# the answers we actually know and leave the rest blank, rather than overlaying
# confident-looking wrong fills. Unclued slots (manual-entry "fill the grid")
# have no clue to be unsure against, so they're always shown. See ARCHITECTURE
# §11 (full-grid accuracy on clued puzzles is signal-limited).
CONFIDENCE_THRESHOLD = 0.6


def _entries_for(puzzle: Puzzle) -> list[Entry]:
    """Build entries: fully-specified slots win; else derive and attach clues."""
    if puzzle.slots:
        return [
            Entry(s.id, s.number, s.direction, tuple((r, c) for r, c in s.cells), s.clue)
            for s in puzzle.slots
        ]

    entries = derive_entries(puzzle.cells)
    if puzzle.clues:
        by_key = {(c.number, c.direction): c.clue for c in puzzle.clues}
        entries = [
            Entry(e.id, e.number, e.direction, e.cells, by_key.get((e.number, e.direction), ""))
            for e in entries
        ]
    return entries


def _painted_letters(
    entries: list[Entry],
    cells: list[list[object]],
    fill: dict[Coord, str],
    assignment: dict[str, tuple[str, float]],
    solved: bool,
    provider: CandidateProvider,
) -> dict[Coord, str]:
    """The letters we trust enough to paint -- the heart of "show only what we know".

    Two sources, in trust order:
      1. **Clue anchors.** Each clued slot's best clue-database answer (confidence
         >= threshold) is laid down highest-confidence first, skipping any that
         conflicts with a given letter or an already-placed stronger answer. This
         surfaces the answers we actually know even when the whole grid can't solve.
      2. **The solved fill.** If the grid fully solved, remaining cells are filled
         from the globally-consistent fill, but only where a covering slot is
         confident -- or unclued, since a manual-entry "fill the grid" has no clue
         to doubt. Anchors win any overlap (a clue answer beats a crossing guess).
    """
    placed: dict[Coord, str] = {}
    for r, row in enumerate(cells):
        for c, value in enumerate(row):
            if isinstance(value, str) and value != "":
                placed[(r, c)] = value.upper()  # given letters are certain

    anchors: list[tuple[float, Entry, str]] = []
    for entry in entries:
        top = provider.top_answer(entry) if entry.clue else None
        if top and top[1] >= CONFIDENCE_THRESHOLD:
            anchors.append((top[1], entry, top[0]))
    anchors.sort(key=lambda a: a[0], reverse=True)
    for _, entry, word in anchors:
        if all(placed.get(cell, ch) == ch for cell, ch in zip(entry.cells, word)):
            placed.update(zip(entry.cells, word))

    if solved:
        for entry in entries:
            if not all(cell in fill for cell in entry.cells):
                continue
            confidence = (
                assignment[entry.id][1]
                if entry.id in assignment
                else provider.confidence(entry, "".join(fill[c] for c in entry.cells))
            )
            if entry.clue and confidence < CONFIDENCE_THRESHOLD:
                continue
            for cell in entry.cells:
                placed.setdefault(cell, fill[cell])  # anchors/givens win

    return placed


def _solve_once(
    cells: list[list[object]], entries: list[Entry], provider: CandidateProvider
) -> tuple[dict[Coord, str], dict[str, tuple[str, float]], dict[Coord, str]]:
    """One CSP solve + paint pass: returns (fill, assignment, painted letters)."""
    solver = Solver(cells, entries, provider)
    solver.solve()
    fill = solver.result_fill()
    assignment = solver.best_assignment
    shown = _painted_letters(entries, cells, fill, assignment, solver.solved, provider)
    return fill, assignment, shown


def _gaps(entries: list[Entry], shown: dict[Coord, str], limit: int) -> list[Gap]:
    """Clued slots not yet confidently filled, with the crossing letters known so
    far, most-constrained first (where the model is most accurate)."""
    ranked: list[tuple[int, Gap]] = []
    for entry in entries:
        if not entry.clue or all(cell in shown for cell in entry.cells):
            continue
        known = sum(1 for cell in entry.cells if cell in shown)
        pattern = "".join(shown.get(cell, ".") for cell in entry.cells)
        ranked.append((known, Gap(entry.id, entry.clue, entry.length, pattern)))
    ranked.sort(key=lambda kg: kg[0], reverse=True)
    return [gap for _, gap in ranked[:limit]]


def solve_puzzle(puzzle: Puzzle) -> SolveResult:
    """Solve a puzzle end to end and return the filled grid + per-slot answers."""
    provider = CandidateProvider(get_wordlist(), get_clue_db())
    entries = _entries_for(puzzle)

    # Warm every clue lookup in one parallel batch before the solver pulls them in
    # one at a time -- the dominant cost on big grids.
    provider.prime_clues(entry.clue for entry in entries)

    fill, assignment, shown_letters = _solve_once(puzzle.cells, entries, provider)

    # Optional LLM booster (off by default): ask a local model about the slots still
    # unresolved, feeding it their crossing letters; inject the answers and re-solve.
    client = get_llm_client()
    if client is not None:
        for _ in range(max(1, llm_config().rounds)):
            gaps = _gaps(entries, shown_letters, llm_config().max_gaps)
            if not gaps:
                break
            extra = boost(gaps, client)
            if not extra:
                break
            for slot_id, scored in extra.items():
                provider.add_candidates(slot_id, scored)
            fill, assignment, shown_letters = _solve_once(puzzle.cells, entries, provider)

    answers: list[SlotAnswer] = []
    for entry in entries:
        letters = [fill.get(cell) for cell in entry.cells]
        if all(letters):
            word = "".join(letters)  # type: ignore[arg-type]
            # Prefer the solver's chosen score; fall back for partial fills.
            if entry.id in assignment:
                confidence = assignment[entry.id][1]
            else:
                confidence = provider.confidence(entry, word)
            answers.append(SlotAnswer(id=entry.id, answer=word, confidence=confidence))
        else:
            answers.append(SlotAnswer(id=entry.id, answer=None, confidence=0.0))

    filled: list[list[str | None]] = []
    fillable = shown = 0
    for r, row in enumerate(puzzle.cells):
        out_row: list[str | None] = []
        for c, value in enumerate(row):
            if value is None:
                out_row.append(None)
                continue
            fillable += 1
            letter = shown_letters.get((r, c))
            if letter:
                out_row.append(letter)
                shown += 1
            else:
                out_row.append("")  # uncertain -> leave blank for the user
        filled.append(out_row)

    # Status reflects what we actually show, not just whether a fill was found.
    if shown == fillable:
        status = "solved"
    elif shown:
        status = "partial"
    else:
        status = "failed"

    return SolveResult(status=status, filled=filled, answers=answers)
