"""Program eligibility gate. Prevents drafting emails to programs that
disqualify Kwabena on hard requirements (e.g. McGill CS PhD needs MSc)."""
from __future__ import annotations
import yaml
from pathlib import Path
from datetime import datetime

PATH = Path(__file__).parent / "programs.yaml"

# User profile: BSc only. Set to True when the MSc is completed.
HAS_MASTERS = False


def _load() -> list[dict]:
    if not PATH.exists(): return []
    return yaml.safe_load(PATH.read_text()) or []


def all_programs() -> list[dict]:
    return _load()


def eligibility(prog: dict) -> dict:
    """Return {eligible: bool, reason: str}."""
    if prog.get("degree") == "PhD" and prog.get("requires_masters_before_phd") and not HAS_MASTERS:
        return {"eligible": False, "reason": "PhD requires MSc; Kwabena has BSc only"}
    if not prog.get("direct_entry", False) and not HAS_MASTERS:
        return {"eligible": False, "reason": "no direct-entry from BSc"}
    return {"eligible": True, "reason": "ok"}


def match_faculty(prof_name: str) -> list[dict]:
    """Return programs that list this prof as affiliated faculty."""
    hits = []
    name_norm = " ".join(prof_name.lower().split())
    for p in _load():
        for f in p.get("affiliated_faculty", []) or []:
            if name_norm in f.lower() or f.lower() in name_norm:
                hits.append(p)
    return hits


def upcoming_deadlines(days: int = 30) -> list[dict]:
    now = datetime.now()
    out = []
    for p in _load():
        try:
            d = datetime.strptime(p.get("deadline", ""), "%Y-%m-%d")
        except Exception:
            continue
        delta = (d - now).days
        if 0 <= delta <= days:
            out.append({"program": p["id"], "days_left": delta,
                        "deadline": p["deadline"], "university": p["university"]})
    return sorted(out, key=lambda x: x["days_left"])
