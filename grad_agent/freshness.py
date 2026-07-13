"""Freshness warnings for the human verification step. Never gates a draft.

Two checks:
  - affiliation_check: does the S2 affiliation still match what the prof's
    live homepage says? S2 records lag reality (people move labs); the
    homepage is fetched at draft time so it IS current.
  - activity_check: has the prof published recently? A silent record can
    mean retirement, industry move, or an S2 record split.
"""
from __future__ import annotations
import datetime
import re

# Words too generic to prove an affiliation match on their own.
GENERIC = {"university", "universite", "universitat", "institute", "college",
           "school", "department", "technology", "science", "sciences",
           "state", "national", "polytechnic", "laboratory", "center",
           "centre", "research"}


def _distinctive_words(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", (text or "").lower())
    return {w for w in words if len(w) > 3 and w not in GENERIC}


def affiliation_check(s2_affiliation: str, homepage_text: str) -> dict:
    """{'match': True|False|None, 'note': str}. None = cannot tell."""
    aff_words = _distinctive_words(s2_affiliation)
    if not s2_affiliation or not aff_words:
        return {"match": None,
                "note": "no S2 affiliation to check, verify lab manually"}
    if not homepage_text:
        return {"match": None,
                "note": "homepage unreachable, verify lab manually"}
    page_words = _distinctive_words(homepage_text)
    hits = aff_words & page_words
    if hits:
        return {"match": True,
                "note": f"S2 affiliation consistent with homepage ({', '.join(sorted(hits)[:3])})"}
    return {"match": False,
            "note": f"MISMATCH: S2 says '{s2_affiliation}' but the homepage "
                    f"does not mention it. They may have moved labs; verify "
                    f"before sending."}


def activity_check(recent_papers: list[dict], stale_years: int = 2) -> dict:
    """{'active': True|False|None, 'note': str} from the papers we already fetched."""
    years = [p.get("year") for p in (recent_papers or []) if p.get("year")]
    if not years:
        return {"active": None, "note": "no dated papers on record"}
    latest = max(years)
    current = datetime.date.today().year
    if current - latest > stale_years:
        return {"active": False,
                "note": f"latest paper is from {latest}; possibly inactive "
                        f"or an incomplete S2 record"}
    return {"active": True, "note": f"publishing recently (latest {latest})"}
