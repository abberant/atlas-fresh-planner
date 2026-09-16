"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

app = FastAPI(title="Atlas Fresh Daily Apple Export Planner", version="0.1.0")

# The Vite dev server runs on another port, so allow it during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_configured,
    }
