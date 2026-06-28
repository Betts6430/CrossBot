import { defineConfig } from 'wxt';

// WXT configuration — https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'CrossBot',
    description: 'Solve and autocomplete crosswords in your browser.',
    permissions: ['storage'],
    // The background worker fetches the local backend (a content-script fetch
    // would hit the host page's CSP). Site match patterns live in each content
    // script's `matches` (see entrypoints/content.ts).
    host_permissions: ['http://localhost:8000/*', 'http://127.0.0.1:8000/*'],
  },
});
