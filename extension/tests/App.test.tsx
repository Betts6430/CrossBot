import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App } from '@/entrypoints/popup/App';

// Stub the persisted preference so the popup test never touches the extension's
// storage (wxt/browser). Backed by a hoisted box so tests can read/seed it.
const prefs = vi.hoisted(() => ({ useBooster: true }));
vi.mock('@/lib/settings', () => ({
  getUseBooster: () => Promise.resolve(prefs.useBooster),
  setUseBooster: (v: boolean) => {
    prefs.useBooster = v;
    return Promise.resolve();
  },
}));

/** Render and flush the mount effects (health check + preference load) inside act(). */
async function renderApp() {
  const utils = render(<App />);
  await act(async () => {});
  return utils;
}

/** A fetch stub that answers /health (with booster availability) and /solve. */
function stubFetch(solveResult: unknown, { booster = false } = {}) {
  const fn = vi.fn((input: string | URL) => {
    const url = String(input);
    if (url.includes('/health')) {
      return Promise.resolve({ ok: true, json: async () => ({ status: 'ok', booster }) } as unknown as Response);
    }
    if (url.includes('/solve')) {
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
  prefs.useBooster = true;
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
    const fetchFn = stubFetch({ status: 'solved', filled, answers: [] });

    const { container } = await renderApp();
    fireEvent.click(screen.getByRole('button', { name: 'Solve' }));

    await waitFor(() => expect(screen.getByText('Solved!')).toBeInTheDocument());
    const solved = container.querySelectorAll('.cell-solved');
    expect(solved.length).toBeGreaterThan(0);
    expect(solved[0]).toHaveTextContent(/[A-E]/);

    // No booster configured -> the request carries no boost flag.
    const solveCall = fetchFn.mock.calls.find((c) => String(c[0]).includes('/solve'));
    expect(String(solveCall![0])).not.toContain('boost');
  });

  it('disables the booster toggle when the backend has no booster', async () => {
    await renderApp();
    const toggle = screen.getByRole('checkbox', { name: /AI booster/i });
    expect(toggle).toBeDisabled();
    expect(screen.getByText(/not configured/i)).toBeInTheDocument();
  });

  it('enables the toggle and sends boost=true when the backend has a booster', async () => {
    const fetchFn = stubFetch({ status: 'solved', filled: [], answers: [] }, { booster: true });

    await renderApp();
    const toggle = screen.getByRole('checkbox', { name: /AI booster/i });
    expect(toggle).toBeEnabled();
    expect(toggle).toBeChecked();

    fireEvent.click(screen.getByRole('button', { name: 'Solve' }));
    await waitFor(() =>
      expect(fetchFn.mock.calls.some((c) => String(c[0]).includes('/solve?boost=true'))).toBe(true),
    );
  });

  it('persists the toggle off and then sends boost=false', async () => {
    const fetchFn = stubFetch({ status: 'solved', filled: [], answers: [] }, { booster: true });

    await renderApp();
    const toggle = screen.getByRole('checkbox', { name: /AI booster/i });
    fireEvent.click(toggle); // uncheck
    expect(prefs.useBooster).toBe(false); // persisted for the content-script path

    fireEvent.click(screen.getByRole('button', { name: 'Solve' }));
    await waitFor(() =>
      expect(fetchFn.mock.calls.some((c) => String(c[0]).includes('/solve?boost=false'))).toBe(true),
    );
  });
});
