"""GET /api/downloads/{filename} — serve agent-generated deliverables.

Serves the CSVs produced by the lead agent as well as the markdown and docx
files produced by the resume optimizer. Restricts to a known extension
allowlist so this endpoint can never accidentally leak files elsewhere.
"""

from pathlib import PurePosixPath

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import DOWNLOADS_DIR

router = APIRouter(prefix="/api/downloads", tags=["downloads"])

# Extension -> (MIME type) mapping doubles as the allowlist.
ALLOWED_EXTENSIONS: dict[str, str] = {
    ".csv": "text/csv",
    ".md": "text/markdown",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".txt": "text/plain",
}


@router.get("/{filename}")
async def download(filename: str) -> FileResponse:
    # Reject traversal attempts — we only serve files with a flat basename.
    safe = PurePosixPath(filename).name
    if safe != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    ext = "." + safe.rsplit(".", 1)[-1].lower() if "." in safe else ""
    media_type = ALLOWED_EXTENSIONS.get(ext)
    if media_type is None:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    path = DOWNLOADS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path=str(path), media_type=media_type, filename=safe)
