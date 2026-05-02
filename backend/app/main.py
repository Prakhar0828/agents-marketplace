"""FastAPI app entrypoint.

Run from the `backend/` directory:

    uvicorn app.main:app --reload --port 8000

In production (single-service deploy), the Vite build output at
`frontend/dist/` is mounted at `/` so the same process serves the SPA, the
REST API, and the WebSocket chat.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import REPO_ROOT, validate_env
from .routes import chat, downloads, marketplace, uploads

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Agent Marketplace", version="0.1.0")

# Dev origins: Vite defaults to 5173; also accept 127.0.0.1 variant. In prod
# we serve the SPA from the same origin so CORS becomes a no-op.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    validate_env()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(marketplace.router)
app.include_router(uploads.router)
app.include_router(downloads.router)
app.include_router(chat.router)


# ── Static SPA ───────────────────────────────────────────────────────────────
# When `frontend/dist/` exists (production build), serve it. In development
# Vite runs on :5173 and this block is inert.
_DIST = REPO_ROOT / "frontend" / "dist"

if _DIST.is_dir():
    _ASSETS = _DIST / "assets"
    if _ASSETS.is_dir():
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """Serve real files under frontend/dist if they exist, otherwise
        fall back to index.html so the React router owns client-side paths
        like `/hire/resume-optimizer`."""
        # Belt-and-braces: don't shadow API or WS routes. They're registered
        # above so specific matches win, but a stray path starting with
        # `api/` or `ws/` here would be a client bug — 404 it cleanly.
        if full_path.startswith(("api/", "ws/")):
            raise HTTPException(status_code=404)

        candidate = (_DIST / full_path).resolve()
        try:
            candidate.relative_to(_DIST.resolve())
        except ValueError:
            raise HTTPException(status_code=404) from None

        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
