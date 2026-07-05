"""Loads the user's CV + transcript PDFs to text, once, cached.

Paths come from profile.yaml (portable) with a fall-back to legacy env vars
(CV_PATH, TRANSCRIPT_PATH) so the pre-refactor single-user setup still works.
"""
from __future__ import annotations
import os
from functools import lru_cache
from pypdf import PdfReader

from . import config as _cfg


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
    p = _cfg.load_profile()
    cv_path = p.cv_path or os.environ.get("CV_PATH", "")
    trans_path = p.transcript_path or os.environ.get("TRANSCRIPT_PATH", "")
    projects = p.projects_dir or os.environ.get("NINTE_ROOT", "")
    return {
        "name": p.name or "the applicant",
        "email_public": os.environ.get("SMTP_USERNAME", ""),
        "portfolio": p.portfolio or os.environ.get("PORTFOLIO_URL", ""),
        "cv_text": _pdf_to_text(cv_path),
        "transcript_text": _pdf_to_text(trans_path),
        "ninte_root": projects,  # legacy key preserved
        "projects_dir": projects,
    }


def summary() -> str:
    p = load()
    cv = p["cv_text"][:400].replace("\n", " ")
    return f"{p['name']} | CV excerpt: {cv}..."
