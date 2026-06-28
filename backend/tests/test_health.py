"""Smoke test: the app boots and /health responds.

Run with: uv run pytest   (or: pytest)
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
