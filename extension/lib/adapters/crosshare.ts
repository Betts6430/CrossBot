import type { Adapter } from '@/lib/adapters';
import type { Cell, ClueRef, Puzzle } from '@/lib/model/puzzle';

// Crosshare is a Next.js app: the whole puzzle is in the __NEXT_DATA__ JSON.
// We take the grid *shape* (blocks vs fillable) and the clues, and ignore the
// embedded solution letters -- we solve it ourselves.

interface CrosshareClue {
  dir: number; // 0 = across, 1 = down
  clue: string;
  num: number;
}

interface CrossharePuzzle {
  size: { rows: number; cols: number };
  grid: string[]; // row-major; "." = block, otherwise the solution letter
  clues: CrosshareClue[];
  title?: string;
}

interface NextData {
  props?: { pageProps?: { puzzle?: CrossharePuzzle } };
}

function readPuzzle(doc: Document): CrossharePuzzle | null {
  const el = doc.getElementById('__NEXT_DATA__');
  if (!el?.textContent) return null;
  try {
    return (JSON.parse(el.textContent) as NextData).props?.pageProps?.puzzle ?? null;
  } catch {
    return null;
  }
}

export const crosshareAdapter: Adapter = {
  id: 'crosshare',

  matches(url, doc) {
    let host: string;
    try {
      host = new URL(url).hostname;
    } catch {
      return false;
    }
    if (!/(^|\.)crosshare\.org$/.test(host)) return false;
    return readPuzzle(doc) !== null;
  },

  extract(doc) {
    const puz = readPuzzle(doc);
    if (!puz) throw new Error('Crosshare puzzle data (__NEXT_DATA__) not found');

    const { rows, cols } = puz.size;
    const cells: Cell[][] = [];
    for (let r = 0; r < rows; r++) {
      const row: Cell[] = [];
      for (let c = 0; c < cols; c++) {
        const value = puz.grid[r * cols + c];
        row.push(value === '.' ? null : ''); // block vs empty fillable
      }
      cells.push(row);
    }

    const clues: ClueRef[] = puz.clues.map((c) => ({
      number: c.num,
      direction: c.dir === 0 ? 'across' : 'down',
      clue: c.clue,
    }));

    const puzzle: Puzzle = {
      source: 'crosshare',
      title: puz.title,
      width: cols,
      height: rows,
      cells,
      clues,
    };
    return puzzle;
  },

  cellElement(doc, row, col) {
    // Crosshare tags each cell with a stable aria-label, e.g. "cell0x0".
    return doc.querySelector(`[aria-label="cell${row}x${col}"]`);
  },
};
