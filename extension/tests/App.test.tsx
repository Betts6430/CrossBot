import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from '@/entrypoints/popup/App';

/** Render and flush the mount health-check so its setState runs inside act(). */
async function renderApp() {
  const utils = render(<App />);
  await act(async () => {});
  return utils;
}

/** A fetch stub that answers /health and /solve. */
function stubFetch(solveResult: unknown) {
  const fn = vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.endsWith('/health')) {
      return Promise.resolve({ ok: true, json: async () => ({ status: 'ok' }) } as unknown as Response);
    }
    if (url.endsWith('/solve')) {
      return Promise.resolve({ ok: true, json: async () => solveResult } as unknown as Response);
    }
    return Promise.reject(new Error(`unexpected fetch: ${url}`));
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

// Block body: do NOT return the spy — Vitest treats a value returned from a
// hook as a teardown callback and would call it (fetch) with no args.
beforeEach(() => {
  stubFetch(null);
});
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('popup App', () => {
  it('renders a 5×5 grid by default', async () => {
    const { container } = await renderApp();
    expect(container.querySelectorAll('.cell')).toHaveLength(25);
  });

  it('types a letter into a selected cell', async () => {
    const { container } = await renderApp();
    const cells = container.querySelectorAll('.cell');
    const grid = container.querySelector('.grid')!;

    fireEvent.mouseDown(cells[0]);
    fireEvent.keyDown(grid, { key: 'B' });

    expect(cells[0]).toHaveTextContent('B');
    expect(cells[0].className).toContain('cell-given');
  });

  it('toggles a black square with Space', async () => {
    const { container } = await renderApp();
    const cells = container.querySelectorAll('.cell');
    const grid = container.querySelector('.grid')!;

    fireEvent.mouseDown(cells[6]); // (1,1)
    fireEvent.keyDown(grid, { key: ' ' });

    expect(cells[6].className).toContain('cell-block');
  });

  it('solves and overlays the filled grid', async () => {
    const filled = Array.from({ length: 5 }, () => ['A', 'B', 'C', 'D', 'E']);
    stubFetch({ status: 'solved', filled, answers: [] });

    const { container } = await renderApp();
    fireEvent.click(screen.getByRole('button', { name: 'Solve' }));

    await waitFor(() => expect(screen.getByText('Solved!')).toBeInTheDocument());
    const solved = container.querySelectorAll('.cell-solved');
    expect(solved.length).toBeGreaterThan(0);
    expect(solved[0]).toHaveTextContent(/[A-E]/);
  });
});
