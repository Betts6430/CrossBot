// User preferences persisted across popup opens and shared with the content
// script, via the extension's local storage (the `storage` permission).

import { browser } from 'wxt/browser';

const USE_BOOSTER_KEY = 'useBooster';

/**
 * Whether to let the backend's optional AI booster answer leftover clues.
 * Defaults to on: the booster is a no-op unless the backend has a local model
 * configured, so the sensible preference is "use it whenever it's available".
 */
export async function getUseBooster(): Promise<boolean> {
  const stored = await browser.storage.local.get(USE_BOOSTER_KEY);
  const value = stored[USE_BOOSTER_KEY];
  return typeof value === 'boolean' ? value : true;
}

export async function setUseBooster(value: boolean): Promise<void> {
  await browser.storage.local.set({ [USE_BOOSTER_KEY]: value });
}
