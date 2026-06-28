import { useState } from 'react';

// Placeholder popup UI. The real popup will host the manual-entry grid editor,
// the "Solve" action, and settings (backend URL, optional LLM toggle).
export function App() {
  const [status] = useState('Scaffolding — solver not wired up yet.');

  return (
    <main className="popup">
      <h1>CrossBot</h1>
      <p className="status">{status}</p>
      <button type="button" disabled>
        Solve current puzzle
      </button>
    </main>
  );
}
