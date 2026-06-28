import type { Puzzle, SolveResult } from '@/lib/model/puzzle';

/** Default address of the local backend (configurable in popup settings). */
export const DEFAULT_BACKEND_URL = 'http://localhost:8000';

/** Send a puzzle to the backend and get back the solved grid. */
export async function solvePuzzle(
  puzzle: Puzzle,
  backendUrl: string = DEFAULT_BACKEND_URL,
): Promise<SolveResult> {
  const res = await fetch(`${backendUrl}/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(puzzle),
  });
  if (!res.ok) {
    throw new Error(`Backend /solve failed: ${res.status} ${res.statusText}`);
  }
  return (await res.json()) as SolveResult;
}

/** Liveness check for the local backend. */
export async function checkHealth(
  backendUrl: string = DEFAULT_BACKEND_URL,
): Promise<boolean> {
  try {
    const res = await fetch(`${backendUrl}/health`);
    return res.ok;
  } catch {
    return false;
  }
}
