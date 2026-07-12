"""External scholarship / fellowship tracker. Reads scholarships.yaml under
GRAD_AGENT_HOME. Same gate-and-deadline pattern as programs.py."""
from __future__ import annotations
import shutil
from datetime import datetime

import yaml

from . import config as _cfg


def _path():
    return _cfg.home() / "scholarships.yaml"


def _load() -> list[dict]:
    p = _path()
    if not p.exists():
        # Seed from the packaged template on first use.
        tmpl = _cfg.TEMPLATES / "scholarships.example.yaml"
        if tmpl.exists():
            _cfg.ensure_home()
            shutil.copy(tmpl, p)
        else:
            return []
    return yaml.safe_load(p.read_text()) or []


def all_scholarships() -> list[dict]:
    return _load()


def eligible(user_region: str = "") -> list[dict]:
    """Scholarships whose eligibility includes the user's region (or 'any').
    With no user_region given, everything is returned."""
    out = []
    for s in _load():
        regions = [str(r).lower() for r in (s.get("eligibility_regions") or [])]
        if not user_region or "any" in regions or user_region.lower() in regions:
            out.append(s)
    return out


def upcoming_deadlines(days: int = 60, user_region: str = "") -> list[dict]:
    now = datetime.now()
    out = []
    for s in eligible(user_region):
        try:
            d = datetime.strptime(str(s.get("deadline", "")), "%Y-%m-%d")
        except ValueError:
            continue
        delta = (d - now).days
        if 0 <= delta <= days:
            out.append({"id": s["id"], "name": s.get("name", s["id"]),
                        "days_left": delta, "deadline": s["deadline"],
                        "url": s.get("url", "")})
    return sorted(out, key=lambda x: x["days_left"])
