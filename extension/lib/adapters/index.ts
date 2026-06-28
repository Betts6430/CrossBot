import type { Puzzle } from '@/lib/model/puzzle';

/**
 * A site adapter knows how to read a crossword off one particular site's DOM
 * and normalize it into a {@link Puzzle}. Adding support for a new site means
 * adding one adapter and registering it below — nothing else changes.
 */
export interface Adapter {
  /** Human-readable id, e.g. "guardian", "amuse". */
  id: string;
  /** Does this adapter apply to the current page? */
  matches(url: string, doc: Document): boolean;
  /** Extract the puzzle from the page. */
  extract(doc: Document): Puzzle;
}

/** All known adapters. Real implementations are added here as they're built. */
export const adapters: Adapter[] = [];

/** Find the first adapter that applies to the current page, if any. */
export function findAdapter(url: string, doc: Document): Adapter | undefined {
  return adapters.find((a) => a.matches(url, doc));
}
