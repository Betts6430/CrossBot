"""Smoke test: the app boots and /health responds.

Run with: uv run pytest   (or: pytest)
"""

import pytest
from fastapi.testclient import TestClient

import app.main as main
from app.config import LLMConfig
from app.main import app

client = TestClient(app)


def test_health_default_reports_no_booster() -> None:
    # No CROSSBOT_LLM set in the test env -> the standard $0 path advertises booster off.
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "booster": False}


def test_health_advertises_booster_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        main, "llm_config",
        lambda: LLMConfig("ollama", "m", "http://x", 2, 5.0, 40, 0.5),
    )
    assert client.get("/health").json() == {"status": "ok", "booster": True}
