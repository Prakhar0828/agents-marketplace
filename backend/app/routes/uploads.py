"""POST /api/uploads/resume — stash a user-uploaded resume PDF.

The chat WebSocket carries only JSON, so binary resume PDFs are uploaded via
a separate HTTP endpoint that returns a short random id. The client then
includes that id alongside the next chat message so the resume_agent can
open the stashed file from disk.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..config import UPLOADS_DIR

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

# 10 MB is plenty for a resume; rejects oversized or binary-misuse uploads.
MAX_BYTES = 10 * 1024 * 1024


class UploadResponse(BaseModel):
    id: str
    filename: str
    size: int


@router.post("/resume", response_model=UploadResponse)
async def upload_resume(file: UploadFile = File(...)) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(
            status_code=413, detail=f"File too large (max {MAX_BYTES // (1024 * 1024)} MB)."
        )
    if not raw.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400, detail="File doesn't look like a valid PDF."
        )

    file_id = secrets.token_urlsafe(16)
    # We save the file with its id so the agent can look it up later. The
    # original filename is preserved in `<id>__<name>.pdf` so downloaders
    # see a sensible suggested name — but for now we just keep <id>.pdf.
    dest = UPLOADS_DIR / f"{file_id}.pdf"
    dest.write_bytes(raw)

    # Also stash the original filename next to it so the agent can surface it
    # in the chat ("Optimizing your resume '<name>.pdf'…").
    _original_name_path(file_id).write_text(Path(file.filename).name)

    return UploadResponse(id=file_id, filename=file.filename, size=len(raw))


def _original_name_path(file_id: str) -> Path:
    return UPLOADS_DIR / f"{file_id}.name"


def load_upload(file_id: str) -> tuple[Path, str] | None:
    """Resolve a file id to (pdf_path, original_filename). Returns None if unknown."""
    pdf = UPLOADS_DIR / f"{file_id}.pdf"
    if not pdf.exists():
        return None
    name_path = _original_name_path(file_id)
    original = name_path.read_text() if name_path.exists() else "resume.pdf"
    return pdf, original
