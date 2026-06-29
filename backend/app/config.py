"""Runtime configuration from environment variables.

Everything here is off/empty by default, so the standard $0 path needs zero setup.
The only configurable subsystem today is the optional LLM booster (see
``app/solver/llm.py``), enabled by setting ``CROSSBOT_LLM=ollama``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class LLMConfig:
    """How (and whether) to call a local model to answer leftover clues."""

    provider: str  # "" = off (default), "ollama" = local Ollama server
    model: str
    url: str
    rounds: int  # propose -> re-solve passes (each pass tightens crossing letters)
    timeout: float  # seconds per model call
    max_gaps: int  # most clues to ask about per pass (caps latency)

    @property
    def enabled(self) -> bool:
        return self.provider == "ollama"


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


@lru_cache(maxsize=1)
def llm_config() -> LLMConfig:
    return LLMConfig(
        provider=os.getenv("CROSSBOT_LLM", "").strip().lower(),
        # Accuracy-leaning local default; override with CROSSBOT_LLM_MODEL (e.g.
        # llama3.1:8b for a lighter/faster machine). Just a string -- no lock-in.
        model=os.getenv("CROSSBOT_LLM_MODEL", "qwen2.5:14b").strip(),
        url=os.getenv("CROSSBOT_LLM_URL", "http://localhost:11434").rstrip("/"),
        rounds=_int("CROSSBOT_LLM_ROUNDS", 2),
        timeout=_float("CROSSBOT_LLM_TIMEOUT", 60.0),
        max_gaps=_int("CROSSBOT_LLM_MAX_GAPS", 40),
    )
