"""Top-level orchestration of a solve.

Pipeline (see docs/ARCHITECTURE.md):
    1. derive entries from the grid (or use those the puzzle carries, with clues)
    2. CSP fill using a CandidateProvider = clue database + word list
    3. (optional, off by default) LLM booster: ask a local model about still-
       unresolved slots, inject its answers, and re-solve -- repeat a few rounds so
       each fill tightens the crossing letters the model sees.
"""

from __future__ import annotations

import math

from app.config import llm_config
from app.data.loaders import get_clue_db, get_wordlist
from app.models import Puzzle, SlotAnswer, SolveResult
from app.solver.candidates import CandidateProvider
from app.solver.csp import Solver
from app.solver.grid import Coord, Entry, derive_entries
from app.solver.llm import Gap, boost as boost_gaps, get_llm_client

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
    solved: bool,
    provider: CandidateProvider,
    corroboration: float,
) -> dict[Coord, str]:
    """The letters we trust enough to paint -- the heart of "show only what we know".

    Three tiers, in trust order; earlier tiers win any overlap:
      1. **Clue anchors + givens.** Each clued slot's best clue-database answer
         (>= threshold) laid down strongest-first, skipping conflicts. These cells
         are *confident* -- trusted independently of the LLM.
      2. **The confident fill** (only if the grid fully solved): cells of slots the
         clue DB scores >= threshold, plus unclued slots (manual-entry "fill the
         grid" has no clue to doubt). Also confident.
      3. **LLM-lifted slots** (only if solved): a slot the booster pushed over the
         threshold paints only where enough of its cells (``corroboration`` of them)
         are already confident from tiers 1-2 -- so the model extends known
         structure but a free-floating guess stays blank.
    """
    placed: dict[Coord, str] = {}
    for r, row in enumerate(cells):
        for c, value in enumerate(row):
            if isinstance(value, str) and value != "":
                placed[(r, c)] = value.upper()  # given letters are certain
    confident: set[Coord] = set(placed)

    anchors: list[tuple[float, Entry, str]] = []
    for entry in entries:
        top = provider.top_clue_answer(entry) if entry.clue else None
        if top and top[1] >= CONFIDENCE_THRESHOLD:
            anchors.append((top[1], entry, top[0]))
    anchors.sort(key=lambda a: a[0], reverse=True)
    for _, entry, word in anchors:
        if all(placed.get(cell, ch) == ch for cell, ch in zip(entry.cells, word)):
            placed.update(zip(entry.cells, word))
            confident.update(entry.cells)

    if solved:
        for entry in entries:  # tier 2: confident DB / unclued fill
            if not all(cell in fill for cell in entry.cells):
                continue
            word = "".join(fill[cell] for cell in entry.cells)
            if not entry.clue or provider.base_confidence(entry, word) >= CONFIDENCE_THRESHOLD:
                placed.update((cell, fill[cell]) for cell in entry.cells if cell not in placed)
                confident.update(entry.cells)

        for entry in entries:  # tier 3: LLM-lifted slots, only where corroborated
            if not entry.clue or not all(cell in fill for cell in entry.cells):
                continue
            word = "".join(fill[cell] for cell in entry.cells)
            if provider.base_confidence(entry, word) >= CONFIDENCE_THRESHOLD:
                continue  # already painted in tier 2
            if provider.confidence(entry, word) < CONFIDENCE_THRESHOLD:
                continue  # not even the LLM is confident
            need = math.ceil(corroboration * len(entry.cells))
            if sum(1 for cell in entry.cells if cell in confident) >= need:
                placed.update((cell, fill[cell]) for cell in entry.cells if cell not in placed)

    return placed


def _solve_once(
    cells: list[list[object]],
    entries: list[Entry],
    provider: CandidateProvider,
    corroboration: float,
) -> tuple[dict[Coord, str], dict[str, tuple[str, float]], dict[Coord, str]]:
    """One CSP solve + paint pass: returns (fill, assignment, painted letters)."""
    solver = Solver(cells, entries, provider)
    solver.solve()
    fill = solver.result_fill()
    shown = _painted_letters(entries, cells, fill, solver.solved, provider, corroboration)
    return fill, solver.best_assignment, shown


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


def solve_puzzle(puzzle: Puzzle, *, boost: bool | None = None) -> SolveResult:
    """Solve a puzzle end to end and return the filled grid + per-slot answers.

    ``boost`` opts the optional LLM booster in or out for this one solve: ``None``
    (the default) or ``True`` uses it when the backend has one configured, ``False``
    skips it entirely. The booster still does nothing unless a local model is set up
    (``CROSSBOT_LLM=ollama``), so the opt-out only matters on a booster-enabled box.
    """
    provider = CandidateProvider(get_wordlist(), get_clue_db())
    entries = _entries_for(puzzle)

    # Warm every clue lookup in one parallel batch before the solver pulls them in
    # one at a time -- the dominant cost on big grids.
    provider.prime_clues(entry.clue for entry in entries)

    cfg = llm_config()
    fill, assignment, shown_letters = _solve_once(
        puzzle.cells, entries, provider, cfg.corroboration
    )

    # Optional LLM booster (off by default): ask a local model about the slots still
    # unresolved, feeding it their crossing letters; inject the answers and re-solve.
    # Stop once a round resolves nothing new (or there's nothing left to ask). A
    # ``boost=False`` opt-out skips the model without even constructing the client.
    client = get_llm_client() if boost is not False else None
    if client is not None:
        for _ in range(max(1, cfg.rounds)):
            gaps = _gaps(entries, shown_letters, cfg.max_gaps)
            if not gaps:
                break
            extra = boost_gaps(gaps, client)
            if not extra:
                break
            for slot_id, scored in extra.items():
                provider.add_candidates(slot_id, scored)
            before = len(shown_letters)
            fill, assignment, shown_letters = _solve_once(
                puzzle.cells, entries, provider, cfg.corroboration
            )
            if len(shown_letters) <= before:
                break  # no progress -- further rounds won't help

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
