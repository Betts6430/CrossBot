"""Optional LLM booster — OFF BY DEFAULT.

Answers clues the database and word list can't, *only if explicitly enabled*.
To keep CrossBot free, the default backend points this at a local model via
Ollama (https://ollama.com); a user may instead supply their own API key.

Disabled by default so the standard experience needs no network and no cost.
Not implemented yet.
"""

from __future__ import annotations

# Feature flag; flipped on via settings once implemented.
LLM_ENABLED = False


def boost(*args: object, **kwargs: object) -> dict[str, list[tuple[str, float]]]:
    """Return extra candidates for unresolved slots. No-op when disabled."""
    if not LLM_ENABLED:
        return {}
    raise NotImplementedError
