import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import { clearOverlay, renderOverlay } from '@/lib/overlay';
import type { Cell, SolveResult } from '@/lib/model/puzzle';

beforeAll(() => {
  // jsdom may lack rAF; the overlay uses it for scroll/resize repaints.
  globalThis.requestAnimationFrame ??= ((cb: FrameRequestCallback) =>
    setTimeout(() => cb(0), 0) as unknown as number) as typeof requestAnimationFrame;
  globalThis.cancelAnimationFrame ??= ((id: number) =>
    clearTimeout(id)) as typeof cancelAnimationFrame;
});

afterEach(() => {
  clearOverlay(document);
  document.body.replaceChildren();
});

/** Build addressable cells with mocked on-screen rects; return a resolver. */
function makeGrid(filled: Cell[][]) {
  filled.forEach((row, r) =>
    row.forEach((_, c) => {
      const el = document.createElement('div');
      el.setAttribute('aria-label', `cell${r}x${c}`);
      el.getBoundingClientRect = () =>
        ({ x: c * 30, y: r * 30, left: c * 30, top: r * 30, width: 30, height: 30,
           right: c * 30 + 30, bottom: r * 30 + 30, toJSON: () => ({}) }) as DOMRect;
      document.body.appendChild(el);
    }),
  );
  return (r: number, c: number) => document.querySelector(`[aria-label="cell${r}x${c}"]`);
}

describe('overlay', () => {
  it('paints a letter over each filled cell, skipping blocks and blanks', () => {
    const filled: Cell[][] = [
      ['C', 'A', 'T'],
      ['', '', null],
    ];
    const result: SolveResult = { status: 'solved', filled, answers: [] };
    renderOverlay(document, result, makeGrid(filled));

    const layer = document.getElementById('crossbot-overlay');
    expect(layer).toBeTruthy();
    expect(layer!.children.length).toBe(3); // C, A, T only
    expect(layer!.textContent).toBe('CAT');
    expect((layer!.children[0] as HTMLElement).style.left).toBe('0px');
    expect((layer!.children[2] as HTMLElement).style.left).toBe('60px');
  });

  it('clearOverlay removes the layer', () => {
    const filled: Cell[][] = [['A']];
    renderOverlay(document, { status: 'solved', filled, answers: [] }, makeGrid(filled));
    expect(document.getElementById('crossbot-overlay')).toBeTruthy();
    clearOverlay(document);
    expect(document.getElementById('crossbot-overlay')).toBeNull();
  });
});
