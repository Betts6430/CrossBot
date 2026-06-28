// Content script: runs on supported puzzle pages.
//
// Responsibilities (not implemented yet):
//   1. Pick the matching site adapter (lib/adapters) for the current page.
//   2. Read the grid + clues into a Puzzle (shared model).
//   3. Send it to the backend (lib/api) and receive a SolveResult.
//   4. Render the answers as an overlay in a Shadow DOM so the host page's
//      CSS can't interfere.
//
// `matches` is scoped to a placeholder for now. Each real adapter narrows this
// to its specific puzzle site(s).
export default defineContentScript({
  matches: ['*://*.example.com/*'],
  main() {
    // TODO: detect puzzle, extract, solve, overlay.
  },
});
