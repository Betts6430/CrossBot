import type { Puzzle, SolveResult } from '@/lib/model/puzzle';

/** Content script -> background: please solve this puzzle via the backend. */
export interface SolveRequest {
  type: 'solve';
  puzzle: Puzzle;
  backendUrl?: string;
  /** Opt the optional AI booster in/out for this solve; omitted = backend default. */
  boost?: boolean;
}

/** Background -> content script: the result, or an error message. */
export type SolveResponse =
  | { ok: true; result: SolveResult }
  | { ok: false; error: string };
