import type { Puzzle, SolveResult } from '@/lib/model/puzzle';

/** Default address of the local backend (configurable in popup settings). */
export const DEFAULT_BACKEND_URL = 'http://localhost:8000';

/** What the backend is up to: reachable, and whether an AI booster is configured. */
export interface BackendStatus {
  online: boolean;
  booster: boolean;
}

/** Build the /solve URL, carrying the optional booster opt-in/out as a query param. */
export function solveUrl(backendUrl: string, boost?: boolean): string {
  const base = `${backendUrl}/solve`;
  return boost === undefined ? base : `${base}?boost=${boost ? 'true' : 'false'}`;
}

/** Send a puzzle to the backend and get back the solved grid. */
export async function solvePuzzle(
  puzzle: Puzzle,
  backendUrl: string = DEFAULT_BACKEND_URL,
  boost?: boolean,
): Promise<SolveResult> {
  const res = await fetch(solveUrl(backendUrl, boost), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(puzzle),
  });
  if (!res.ok) {
    throw new Error(`Backend /solve failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SolveResult;
}

/** Liveness check for the local backend, plus whether a booster is available. */
export async function checkHealth(
  backendUrl: string = DEFAULT_BACKEND_URL,
): Promise<BackendStatus> {
  try {
    const res = await fetch(`${backendUrl}/health`);
    if (!res.ok) return { online: false, booster: false };
    const body = (await res.json()) as { booster?: boolean };
    return { online: true, booster: body.booster === true };
  } catch {
    return { online: false, booster: false };
  }
}
