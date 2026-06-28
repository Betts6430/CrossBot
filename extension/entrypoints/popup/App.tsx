import { useEffect, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { Cell } from '@/lib/model/puzzle';
import { DEFAULT_BACKEND_URL, checkHealth, solvePuzzle } from '@/lib/api/client';
import { buildPuzzle, emptyGrid, resizeGrid } from '@/lib/grid';
import { GridEditor } from './GridEditor';

const MIN = 2;
const MAX = 15;
const clampSize = (n: number) => Math.max(MIN, Math.min(MAX, Number.isFinite(n) ? n : MIN));

export function App() {
  const [width, setWidth] = useState(5);
  const [height, setHeight] = useState(5);
  const [cells, setCells] = useState<Cell[][]>(() => emptyGrid(5, 5));
  const [selected, setSelected] = useState<[number, number] | null>(null);
  const [solution, setSolution] = useState<Cell[][] | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);

  const backendUrl = DEFAULT_BACKEND_URL;

  useEffect(() => {
    let active = true;
    checkHealth(backendUrl).then((ok) => active && setOnline(ok));
    return () => {
      active = false;
    };
  }, [backendUrl]);

  function resize(w: number, h: number) {
    setWidth(w);
    setHeight(h);
    setCells((prev) => resizeGrid(prev, w, h));
    setSolution(null);
    setSelected(null);
  }

  function setCell(r: number, c: number, value: Cell) {
    setCells((prev) => {
      const next = prev.map((row) => row.slice());
      next[r][c] = value;
      return next;
    });
    setSolution(null);
  }

  function clearGrid() {
    setCells(emptyGrid(width, height));
    setSolution(null);
    setSelected(null);
    setStatus('');
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    if (!selected) return;
    const [r, c] = selected;
    const { key } = e;

    if (key === 'ArrowRight') setSelected([r, Math.min(width - 1, c + 1)]);
    else if (key === 'ArrowLeft') setSelected([r, Math.max(0, c - 1)]);
    else if (key === 'ArrowUp') setSelected([Math.max(0, r - 1), c]);
    else if (key === 'ArrowDown') setSelected([Math.min(height - 1, r + 1), c]);
    else if (key === ' ' || key === '#') setCell(r, c, cells[r][c] === null ? '' : null);
    else if (key === 'Backspace' || key === 'Delete') setCell(r, c, '');
    else if (/^[a-zA-Z]$/.test(key)) {
      setCell(r, c, key.toUpperCase());
      if (c < width - 1) setSelected([r, c + 1]);
    } else return; // let other keys (Tab, etc.) behave normally

    e.preventDefault();
  }

  async function solve() {
    setBusy(true);
    setStatus('Solving…');
    try {
      const result = await solvePuzzle(buildPuzzle(width, height, cells), backendUrl);
      setSolution(result.filled);
      setStatus(
        result.status === 'solved'
          ? 'Solved!'
          : result.status === 'partial'
            ? 'Partial fill — no complete solution found.'
            : 'No fill found.',
      );
    } catch (err) {
      setStatus(`Error: ${(err as Error).message}. Is the backend running?`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="popup">
      <header className="topbar">
        <h1>CrossBot</h1>
        <span
          className={`dot ${online === null ? 'dot-unknown' : online ? 'dot-on' : 'dot-off'}`}
          title={`Backend: ${backendUrl}`}
        />
      </header>

      <div className="controls">
        <label>
          W
          <input
            type="number"
            min={MIN}
            max={MAX}
            value={width}
            onChange={(e) => resize(clampSize(+e.target.value), height)}
          />
        </label>
        <label>
          H
          <input
            type="number"
            min={MIN}
            max={MAX}
            value={height}
            onChange={(e) => resize(width, clampSize(+e.target.value))}
          />
        </label>
        <button type="button" onClick={clearGrid}>
          Clear
        </button>
      </div>

      <GridEditor
        cells={cells}
        solution={solution}
        selected={selected}
        onSelect={(r, c) => setSelected([r, c])}
        onKeyDown={onKeyDown}
      />

      <p className="hint">
        Click a square, then type. <kbd>Space</kbd> = black square, <kbd>⌫</kbd> = clear.
      </p>

      <div className="actions">
        <button type="button" onClick={solve} disabled={busy || online === false}>
          {busy ? 'Solving…' : 'Solve'}
        </button>
        {solution && (
          <button type="button" onClick={() => { setSolution(null); setStatus(''); }}>
            Edit
          </button>
        )}
      </div>

      <p className="status">
        {online === false ? `Backend not reachable at ${backendUrl}` : status}
      </p>
    </main>
  );
}
