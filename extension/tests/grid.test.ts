import { describe, expect, it } from 'vitest';
import { buildPuzzle, emptyGrid, resizeGrid } from '@/lib/grid';

describe('grid helpers', () => {
  it('emptyGrid builds an h×w grid of empty cells', () => {
    const g = emptyGrid(3, 2);
    expect(g).toHaveLength(2); // height rows
    expect(g[0]).toHaveLength(3); // width cols
    expect(g.flat().every((c) => c === '')).toBe(true);
  });

  it('resizeGrid preserves overlap and pads new cells empty', () => {
    const g = [
      ['A', 'B'],
      ['C', 'D'],
    ];
    const r = resizeGrid(g, 3, 3);
    expect(r).toHaveLength(3);
    expect(r[0]).toHaveLength(3);
    expect(r[0][0]).toBe('A');
    expect(r[1][1]).toBe('D');
    expect(r[2][2]).toBe(''); // newly added cell
  });

  it('buildPuzzle marks source manual and omits slots', () => {
    const p = buildPuzzle(2, 2, emptyGrid(2, 2));
    expect(p.source).toBe('manual');
    expect(p.width).toBe(2);
    expect(p.height).toBe(2);
    expect(p.slots).toBeUndefined(); // backend derives them
  });
});
