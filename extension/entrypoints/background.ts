import { browser } from 'wxt/browser';
import { DEFAULT_BACKEND_URL, solveUrl } from '@/lib/api/client';
import type { SolveRequest, SolveResponse } from '@/lib/messaging';

// The background worker does the backend fetch: a content script's fetch to
// localhost would be blocked by the host page's CSP, but the worker isn't
// subject to it (and has the localhost host permission).
export default defineBackground(() => {
  browser.runtime.onMessage.addListener((message: unknown): Promise<SolveResponse> | undefined => {
    const msg = message as SolveRequest;
    if (msg?.type !== 'solve') return undefined;

    return (async (): Promise<SolveResponse> => {
      try {
        const res = await fetch(solveUrl(msg.backendUrl ?? DEFAULT_BACKEND_URL, msg.boost), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(msg.puzzle),
        });
        if (!res.ok) throw new Error(`backend ${res.status} ${res.statusText}`);
        return { ok: true, result: await res.json() };
      } catch (e) {
        return { ok: false, error: (e as Error).message };
      }
    })();
  });
});
