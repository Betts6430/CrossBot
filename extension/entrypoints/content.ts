import { browser } from 'wxt/browser';
import { findAdapter } from '@/lib/adapters';
import { clearOverlay, renderOverlay } from '@/lib/overlay';
import type { SolveRequest, SolveResponse } from '@/lib/messaging';

// Runs on supported puzzle pages: detect the puzzle, and on a click extract it,
// ask the backend (via the background worker) to solve it, and overlay answers.
export default defineContentScript({
  matches: ['*://crosshare.org/crosswords/*'],
  main() {
    const adapter = findAdapter(location.href, document);
    if (!adapter) return;

    const btn = document.createElement('button');
    btn.id = 'crossbot-solve';
    btn.textContent = 'Solve with CrossBot';
    Object.assign(btn.style, {
      position: 'fixed',
      bottom: '16px',
      right: '16px',
      zIndex: '2147483647',
      padding: '10px 14px',
      borderRadius: '8px',
      border: 'none',
      background: '#1a56db',
      color: '#fff',
      font: '600 14px system-ui, -apple-system, sans-serif',
      boxShadow: '0 2px 8px rgba(0,0,0,.3)',
      cursor: 'pointer',
    });
    document.body.appendChild(btn);

    btn.addEventListener('click', async () => {
      btn.disabled = true;
      btn.textContent = 'Solving…';
      clearOverlay(document);
      try {
        const puzzle = adapter.extract(document);
        const resp = (await browser.runtime.sendMessage({
          type: 'solve',
          puzzle,
        } satisfies SolveRequest)) as SolveResponse;
        if (!resp.ok) throw new Error(resp.error);
        renderOverlay(document, resp.result, (r, c) => adapter.cellElement(document, r, c));
        btn.textContent = resp.result.status === 'solved' ? 'Solved ✓ (redo)' : 'Partial — see grid';
      } catch (e) {
        console.error('[CrossBot]', e);
        btn.textContent = 'Error — is the backend running?';
      } finally {
        btn.disabled = false;
      }
    });
  },
});
