"""Optional LLM booster -- OFF BY DEFAULT.

Answers clues the database and word list can't, *only if explicitly enabled*. To
keep CrossBot free, the default backend points this at a local model via Ollama
(https://ollama.com); the standard experience needs no network and no cost.

The booster is fed only the slots the hybrid solver left unresolved, each with its
length and the crossing letters already fixed by the grid (a pattern like
``P.R.S``) -- those constraints are what make a model accurate here. It returns
extra scored candidates that flow back through ``CandidateProvider`` exactly like
clue-database answers, so the CSP still owns making every crossing agree.

Enable with ``CROSSBOT_LLM=ollama`` (see ``app/config.py``); ``engine.py`` then
runs it on unresolved slots and re-solves. A solve can also opt out per request
(``POST /solve?boost=false``), surfaced as the extension's "use AI booster" toggle.
This module is the client + prompt/parse layer.
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Protocol

from app.config import llm_config

# An LLM answer's top guess sits just above the paint threshold (0.6), so it can
# show only once crossings corroborate it; lower-ranked guesses feed the CSP but
# won't be painted on their own. This is the main calibration knob.
_BASE_CONFIDENCE = 0.62
_RANK_STEP = 0.03
_CONFIDENCE_FLOOR = 0.50
_MAX_PER_SLOT = 5


@dataclass(frozen=True)
class Gap:
    """An unresolved slot to ask the model about."""

    slot_id: str
    clue: str
    length: int
    pattern: str  # crossing letters fixed so far, '.' for unknown (e.g. "P.R.S")


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str: ...


class OllamaClient:
    """Calls a local Ollama server's /api/generate (stdlib HTTP, no extra deps)."""

    def __init__(self, model: str, url: str, timeout: float) -> None:
        self.model = model
        self.url = url
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        body = json.dumps(
            {"model": self.model, "prompt": prompt, "stream": False,
             "options": {"temperature": 0.0}}
        ).encode()
        req = urllib.request.Request(
            f"{self.url}/api/generate", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (localhost)
            return json.loads(resp.read()).get("response", "")


def get_llm_client() -> LLMClient | None:
    """The configured client, or None when the booster is off (the default)."""
    cfg = llm_config()
    if cfg.provider == "ollama":
        return OllamaClient(cfg.model, cfg.url, cfg.timeout)
    return None


def build_prompt(gaps: list[Gap]) -> str:
    lines = [
        f'{g.slot_id}: "{g.clue}" - {g.length} letters, pattern {g.pattern.replace(".", "_")}'
        for g in gaps
    ]
    return (
        "You are an expert crossword solver. For each clue id below, give up to "
        f"{_MAX_PER_SLOT} likely answers, best first. Each answer must be exactly "
        "the stated number of letters, UPPERCASE A-Z only (no spaces or "
        "punctuation), and must match the pattern, where an underscore is unknown "
        "and a letter is already fixed by a crossing.\n"
        "Reply with ONLY a JSON object mapping each id to an array of answers, "
        'e.g. {"1A": ["PARIS"], "7D": ["PAR", "PUT"]}.\n\n'
        "Clues:\n" + "\n".join(lines)
    )


def _matches(pattern: str, word: str) -> bool:
    return all(p == "." or p == c for p, c in zip(pattern, word))


def _extract_json(raw: str) -> object:
    text = raw.strip()
    if text.startswith("```"):  # ```json ... ``` fences
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def parse_answers(raw: str, gaps: list[Gap]) -> dict[str, list[tuple[str, float]]]:
    """Validate a model reply into per-slot scored candidates.

    Drops anything that isn't the right length, doesn't fit the known crossings, or
    isn't plain letters -- so a hallucinated non-fit never reaches the grid.
    """
    obj = _extract_json(raw)
    if not isinstance(obj, dict):
        return {}
    by_id = {g.slot_id: g for g in gaps}

    out: dict[str, list[tuple[str, float]]] = {}
    for slot_id, answers in obj.items():
        gap = by_id.get(slot_id)
        if gap is None or not isinstance(answers, list):
            continue
        scored: list[tuple[str, float]] = []
        seen: set[str] = set()
        for answer in answers:
            if not isinstance(answer, str):
                continue
            word = re.sub(r"[^A-Za-z]", "", answer).upper()
            if len(word) != gap.length or word in seen or not _matches(gap.pattern, word):
                continue
            seen.add(word)
            conf = max(_CONFIDENCE_FLOOR, _BASE_CONFIDENCE - _RANK_STEP * len(scored))
            scored.append((word, conf))
            if len(scored) >= _MAX_PER_SLOT:
                break
        if scored:
            out[slot_id] = scored
    return out


def boost(gaps: Iterable[Gap], client: LLMClient) -> dict[str, list[tuple[str, float]]]:
    """Extra candidates for unresolved slots. Never raises -- a failed/absent model
    just yields no extras, so a solve is never broken by the booster."""
    gaps = list(gaps)
    if not gaps:
        return {}
    try:
        raw = client.generate(build_prompt(gaps))
    except Exception:  # noqa: BLE001 -- network boundary; degrade to no-op
        return {}
    return parse_answers(raw, gaps)
