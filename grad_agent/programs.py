"""Program eligibility gate. Reads from the user's programs.yaml under
GRAD_AGENT_HOME. Uses profile.degree_status to gate PhD applications."""
from __future__ import annotations
import yaml
from datetime import datetime

from . import config as _cfg


def _has_masters() -> bool:
    try:
        return _cfg.load_profile().has_masters
    except Exception:
        return False


def _load() -> list[dict]:
    p = _cfg.programs_path()
    if not p.exists(): return []
    return yaml.safe_load(p.read_text()) or []


def all_programs() -> list[dict]:
    return _load()


def eligibility(prog: dict) -> dict:
    """Return {eligible: bool, reason: str}."""
    if prog.get("degree") == "PhD" and prog.get("requires_masters_before_phd") and not _has_masters():
        return {"eligible": False,
                "reason": "PhD requires MSc first; profile.degree_status is bachelors"}
    if not prog.get("direct_entry", False) and not _has_masters():
        return {"eligible": False, "reason": "no direct-entry from bachelors"}
    return {"eligible": True, "reason": "ok"}


def match_faculty(prof_name: str) -> list[dict]:
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
