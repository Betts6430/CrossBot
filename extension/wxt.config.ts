import { defineConfig } from 'wxt';

// WXT configuration — https://wxt.dev/api/config.html
export default defineConfig({
  modules: ['@wxt-dev/module-react'],
  manifest: {
    name: 'CrossBot',
    description: 'Solve and autocomplete crosswords in your browser.',
    permissions: ['storage', 'activeTab', 'scripting'],
    // Host permissions are added per site as adapters are built (see
    // lib/adapters). Kept empty for now so the extension asks for nothing
    // it doesn't yet use.
    host_permissions: [],
  },
});
