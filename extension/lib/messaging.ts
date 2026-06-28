import type { Puzzle, SolveResult } from '@/lib/model/puzzle';

/** Content script -> background: please solve this puzzle via the backend. */
export interface SolveRequest {
  type: 'solve';
  puzzle: Puzzle;
  backendUrl?: string;
}

/** Background -> content script: the result, or an error message. */
export type SolveResponse =
  | { ok: true; result: SolveResult }
  | { ok: false; error: string };
