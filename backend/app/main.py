"""FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.errors import register_error_handlers
from app.api.routes_assistant import router as assistant_router
from app.api.routes_plan import router as plan_router
from app.config import REPO_ROOT, get_settings

app = FastAPI(title="Atlas Fresh Daily Apple Export Planner", version="0.1.0")

# The Vite dev server runs on another port, so allow it during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)


@app.get("/api/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "ai_configured": settings.ai_configured,
    }


app.include_router(plan_router)
app.include_router(assistant_router)

# In production the same server also serves the built frontend. Mounted last so
# it never shadows an /api route.
FRONTEND_DIST: Path = REPO_ROOT / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
