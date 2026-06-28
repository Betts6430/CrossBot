# CrossBot extension

Browser extension (Manifest V3) built with [WXT](https://wxt.dev) +
TypeScript + React. Reads a crossword off the page (or via manual entry), sends
it to the local backend, and overlays the answers.

## Develop

```bash
npm install        # also runs `wxt prepare`, generating .wxt/
npm run dev        # Chrome dev build with HMR
npm run dev:firefox
```

## Build

```bash
npm run build      # production build into .output/
npm run zip        # packaged .zip for store upload
```

## Layout

```
entrypoints/
  background.ts        MV3 service worker (message routing)
  content.ts           runs on puzzle pages: extract → solve → overlay
  popup/               toolbar UI: manual entry, Solve, settings
lib/
  model/               TypeScript mirror of shared/puzzle.schema.json
  api/                 backend client (/solve, /health)
  adapters/            one Adapter per supported site
```

The extension talks to the backend at `http://localhost:8000` by default (see
`lib/api/client.ts`). Site support is added by writing one adapter in
`lib/adapters/` and registering it — see `lib/adapters/index.ts`.
