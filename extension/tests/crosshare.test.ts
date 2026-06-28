import { describe, expect, it } from 'vitest';
import { crosshareAdapter } from '@/lib/adapters/crosshare';
import fixture from './fixtures/crosshare-mini.json';

const PAGE = 'https://crosshare.org/crosswords/abc/mini';

function docWith(puzzle: unknown): Document {
  const d = document.implementation.createHTMLDocument('t');
  const s = d.createElement('script');
  s.id = '__NEXT_DATA__';
  s.type = 'application/json';
  s.textContent = JSON.stringify({ props: { pageProps: { puzzle } } });
  d.body.appendChild(s);
  return d;
}

describe('crosshare adapter', () => {
  it('matches only crosshare pages that carry puzzle data', () => {
    expect(crosshareAdapter.matches(PAGE, docWith(fixture))).toBe(true);
    expect(crosshareAdapter.matches('https://example.com/x', docWith(fixture))).toBe(false);
    const empty = document.implementation.createHTMLDocument('t');
    expect(crosshareAdapter.matches(PAGE, empty)).toBe(false);
  });

  it('extracts the grid shape and ignores the embedded solution', () => {
    const p = crosshareAdapter.extract(docWith(fixture));
    expect([p.width, p.height]).toEqual([5, 5]);
    expect(p.source).toBe('crosshare');
    // Row 0 is "P U B . ." -> two trailing blocks; fillable cells come back "".
    expect(p.cells[0][0]).toBe('');
    expect(p.cells[0][3]).toBeNull();
    expect(p.cells[4][0]).toBeNull();
    expect(p.cells[2][2]).toBe('');
  });

  it('maps clues with dir 0 = across, dir 1 = down', () => {
    const p = crosshareAdapter.extract(docWith(fixture));
    expect(p.clues).toHaveLength(10);
    expect(p.clues!.filter((c) => c.direction === 'across')).toHaveLength(5);
    expect(p.clues!.filter((c) => c.direction === 'down')).toHaveLength(5);
    const oneAcross = p.clues!.find((c) => c.number === 1 && c.direction === 'across');
    expect(oneAcross?.clue).toBe('Pint place');
  });

  it('resolves cell elements by aria-label', () => {
    const d = document.implementation.createHTMLDocument('t');
    const cell = d.createElement('div');
    cell.setAttribute('aria-label', 'cell2x3');
    d.body.appendChild(cell);
    expect(crosshareAdapter.cellElement(d, 2, 3)).toBe(cell);
    expect(crosshareAdapter.cellElement(d, 0, 0)).toBeNull();
  });
});
