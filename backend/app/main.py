"""FastAPI application entry point.

Run locally with:
    uv run uvicorn app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app = FastAPI(title="CrossBot Backend", version="0.0.1")

# The extension calls this server from chrome-extension:// origins. For local,
# single-user use this is permissive; lock it down to specific extension ID(s)
# before any non-local deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check used by the extension to confirm the backend is up."""
    return {"status": "ok"}
