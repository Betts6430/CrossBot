import type { Cell, Puzzle } from '@/lib/model/puzzle';

/** A fresh grid of empty (fillable) cells. */
export function emptyGrid(width: number, height: number): Cell[][] {
  return Array.from({ length: height }, () =>
    Array.from({ length: width }, () => '' as Cell),
  );
}

/** Resize a grid, preserving overlapping cells and filling new ones empty. */
export function resizeGrid(cells: Cell[][], width: number, height: number): Cell[][] {
  return Array.from({ length: height }, (_, r) =>
    Array.from({ length: width }, (_, c) => (cells[r]?.[c] ?? '') as Cell),
  );
}

/** Build a Puzzle for the backend from the manual-entry grid (no slots). */
export function buildPuzzle(width: number, height: number, cells: Cell[][]): Puzzle {
  return { source: 'manual', width, height, cells };
}
