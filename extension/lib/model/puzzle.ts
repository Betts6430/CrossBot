// TypeScript mirror of shared/puzzle.schema.json.
// Keep this in sync with backend/app/models.py when the schema changes.

/** A grid cell: null = block, "" = empty fillable, "A"… = a given letter. */
export type Cell = string | null;

/** A [row, col] coordinate, zero-indexed from the top-left. */
export type Coord = [row: number, col: number];

export type Direction = 'across' | 'down';

/** One answer position (an across or down entry). */
export interface Slot {
  /** Stable id, e.g. "1A" or "5D". */
  id: string;
  /** Grid number shown at the slot's first cell. */
  number: number;
  direction: Direction;
  /** Ordered cell coordinates from start to end. */
  cells: Coord[];
  /** Number of cells; equals `cells.length`. */
  length: number;
  /** Clue text; may be empty if unknown. */
  clue: string;
}

/** A normalized crossword. Produced by adapters, manual entry, or file import. */
export interface Puzzle {
  /** Origin, e.g. "manual", "guardian", "amuse". */
  source?: string;
  title?: string;
  width: number;
  height: number;
  /** Row-major grid; `cells[row][col]`. */
  cells: Cell[][];
  /** Optional: manual entry omits these and the backend derives them. */
  slots?: Slot[];
}

/** The solver's answer for a single slot. */
export interface SlotAnswer {
  /** Matches `Slot.id`. */
  id: string;
  /** Uppercase letters (length == slot length), or null if unsolved. */
  answer: string | null;
  /** Solver confidence, 0..1. */
  confidence: number;
}

export type SolveStatus = 'solved' | 'partial' | 'failed';

/** What `POST /solve` returns. Consumed by the overlay / popup UI. */
export interface SolveResult {
  status: SolveStatus;
  /** The grid with answers filled in, same shape as `Puzzle.cells`. */
  filled: Cell[][];
  answers: SlotAnswer[];
}
