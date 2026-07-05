"""Semantic Scholar client. Used to verify a candidate is actually faculty
and to pull a small set of their recent papers for multi-paper hooks."""
from __future__ import annotations
import httpx, time

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS_AUTHOR = "authorId,name,affiliations,hIndex,paperCount,homepage,url"
FIELDS_PAPERS = "title,abstract,year,venue,authors,externalIds"


def _get(path: str, params: dict) -> dict | None:
    for _ in range(3):
        r = httpx.get(f"{BASE}{path}", params=params, timeout=30,
                      headers={"User-Agent": "grad-agent/1.0"})
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429:
            time.sleep(2); continue
        return None
    return None


def find_author(name: str) -> dict | None:
    """Best match by name. Returns first author record with h-index > 0."""
    j = _get("/author/search", {"query": name, "fields": FIELDS_AUTHOR, "limit": 5})
    if not j: return None
    for a in j.get("data", []):
        if (a.get("hIndex") or 0) >= 1:
            return a
    return (j.get("data") or [None])[0]


def is_faculty(author: dict) -> tuple[bool, str]:
    """Heuristic: at least one affiliation, h-index >= 8, paper count >= 15.
    A student can have h-index up to ~5. Adjust upward if too permissive."""
    if not author: return False, "no author record"
    h = author.get("hIndex") or 0
    n = author.get("paperCount") or 0
    aff = author.get("affiliations") or []
    if not aff: return False, "no affiliation on record"
    if h < 6: return False, f"h-index {h} too low"
    if n < 12: return False, f"paper count {n} too low"
    return True, f"h={h} n={n} aff={aff[0]}"


def recent_papers(author_id: str, limit: int = 5) -> list[dict]:
    j = _get(f"/author/{author_id}/papers",
             {"fields": FIELDS_PAPERS, "limit": limit})
    if not j: return []
    out = []
    for p in j.get("data", []):
        if not p.get("abstract"): continue
        out.append({
            "title": p.get("title", ""),
            "abstract": p.get("abstract", "")[:1600],
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "url": (p.get("externalIds", {}) or {}).get("ArXiv"),
        })
    out.sort(key=lambda x: x.get("year") or 0, reverse=True)
    return out


def verify_by_name(name: str) -> dict:
    a = find_author(name)
    if not a: return {"ok": False, "reason": "no match on semantic scholar"}
    ok, reason = is_faculty(a)
    return {
        "ok": ok, "reason": reason, "author_id": a.get("authorId"),
        "name": a.get("name"), "h_index": a.get("hIndex"),
        "paper_count": a.get("paperCount"),
        "affiliations": a.get("affiliations") or [],
        "homepage": a.get("homepage"),
        "s2_url": a.get("url"),
    }
