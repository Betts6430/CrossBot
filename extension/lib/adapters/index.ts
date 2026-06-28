import type { Puzzle } from '@/lib/model/puzzle';
import { crosshareAdapter } from '@/lib/adapters/crosshare';

/**
 * A site adapter reads a crossword off one particular site's DOM and normalizes
 * it into a {@link Puzzle}, and maps grid coordinates back to DOM cells so the
 * overlay can paint answers in place. Adding a site = adding one adapter here.
 */
export interface Adapter {
  /** Human-readable id, e.g. "crosshare". */
  id: string;
  /** Does this adapter apply to the current page? */
  matches(url: string, doc: Document): boolean;
  /** Extract the puzzle (grid shape + clues) from the page. */
  extract(doc: Document): Puzzle;
  /** The DOM element for cell (row, col), used to position the overlay. */
  cellElement(doc: Document, row: number, col: number): Element | null;
}

/** All known adapters. */
export const adapters: Adapter[] = [crosshareAdapter];

/** Find the first adapter that applies to the current page, if any. */
export function findAdapter(url: string, doc: Document): Adapter | undefined {
  return adapters.find((a) => a.matches(url, doc));
}
