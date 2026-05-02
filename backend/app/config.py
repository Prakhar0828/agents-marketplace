"""Runtime configuration. Loads from the repo-root .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

# .env lives at the repo root (one level above backend/)
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

# Where generated CSVs / optimized resumes are written. Kept inside the repo so
# the download route can serve them without extra path gymnastics.
DOWNLOADS_DIR = REPO_ROOT / "backend" / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Where uploaded resume PDFs are stashed, keyed by a random file id.
UPLOADS_DIR = REPO_ROOT / "backend" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def validate_env() -> None:
    missing = [
        k
        for k, v in (
            ("OPENAI_API_KEY", OPENAI_API_KEY),
            ("APIFY_API_TOKEN", APIFY_API_TOKEN),
        )
        if not v
    ]
    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}. "
            "Add them to the repo-root .env file."
        )
