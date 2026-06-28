import type { SolveResult } from '@/lib/model/puzzle';

// Solved letters are painted in our own fixed-position layer appended to
// <body> (outside the site's React root, so it can't be wiped), with one
// element per cell anchored to that cell's on-screen rect. This is renderer-
// agnostic, so it works for DOM grids now and canvas grids (Amuse) later.

const LAYER_ID = 'crossbot-overlay';
const Z = '2147483646';

type CellResolver = (row: number, col: number) => Element | null;

let cleanup: (() => void) | null = null;

export function clearOverlay(doc: Document): void {
  doc.getElementById(LAYER_ID)?.remove();
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
}

export function renderOverlay(doc: Document, result: SolveResult, cellAt: CellResolver): void {
  clearOverlay(doc);

  const layer = doc.createElement('div');
  layer.id = LAYER_ID;
  Object.assign(layer.style, {
    position: 'fixed',
    inset: '0',
    pointerEvents: 'none',
    zIndex: Z,
  });
  doc.body.appendChild(layer);

  const paint = () => {
    layer.replaceChildren();
    result.filled.forEach((row, r) => {
      row.forEach((letter, c) => {
        if (!letter) return; // block (null) or empty ("")
        const el = cellAt(r, c);
        if (!el) return;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        const span = doc.createElement('div');
        span.textContent = letter;
        Object.assign(span.style, {
          position: 'fixed',
          left: `${rect.left}px`,
          top: `${rect.top}px`,
          width: `${rect.width}px`,
          height: `${rect.height}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          font: `600 ${Math.floor(rect.height * 0.55)}px system-ui, -apple-system, sans-serif`,
          color: '#1a56db',
          pointerEvents: 'none',
        });
        layer.appendChild(span);
      });
    });
  };

  let raf = 0;
  const onReflow = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(paint);
  };

  paint();
  window.addEventListener('scroll', onReflow, true);
  window.addEventListener('resize', onReflow);
  cleanup = () => {
    cancelAnimationFrame(raf);
    window.removeEventListener('scroll', onReflow, true);
    window.removeEventListener('resize', onReflow);
  };
}
