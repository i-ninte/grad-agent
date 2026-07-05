"""Loads CV + transcript once, caches as text. Used by every drafter."""
from __future__ import annotations
import os
from functools import lru_cache
from pypdf import PdfReader


def _pdf_to_text(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    try:
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return f"[pdf read error: {e}]"


@lru_cache(maxsize=1)
def load() -> dict:
    return {
        "name": "Kwabena Obeng",
        "email_public": os.environ.get("SMTP_USERNAME", ""),
        "portfolio": os.environ.get("PORTFOLIO_URL", ""),
        "cv_text": _pdf_to_text(os.environ.get("CV_PATH", "")),
        "transcript_text": _pdf_to_text(os.environ.get("TRANSCRIPT_PATH", "")),
        "ninte_root": os.environ.get("NINTE_ROOT", ""),
    }


def summary() -> str:
    p = load()
    cv = p["cv_text"][:400].replace("\n", " ")
    return f"{p['name']} | CV excerpt: {cv}..."
