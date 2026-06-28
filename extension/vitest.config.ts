import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

// The popup uses no chrome.* APIs (only fetch), so it runs under jsdom.
export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('.', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    include: ['tests/**/*.test.{ts,tsx}'],
  },
});
