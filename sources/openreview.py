"""OpenReview API v2 — recent accepted papers at top venues."""
from __future__ import annotations
import httpx


VENUES = {
    "iclr": "ICLR.cc/2025/Conference",
    "neurips": "NeurIPS.cc/2024/Conference",
    "colm": "colmweb.org/COLM/2024/Conference",
}


def recent(venue: str = "iclr", limit: int = 25) -> list[dict]:
    vid = VENUES.get(venue, venue)
    url = "https://api2.openreview.net/notes"
    params = {"content.venueid": vid, "limit": limit, "sort": "cdate:desc"}
    try:
        r = httpx.get(url, params=params, timeout=30)
        notes = r.json().get("notes", [])
    except Exception:
        return []
    out = []
    for n in notes:
        c = n.get("content", {})
        out.append({
            "title": (c.get("title", {}) or {}).get("value", ""),
            "authors": (c.get("authors", {}) or {}).get("value", []),
            "abstract": ((c.get("abstract", {}) or {}).get("value", "") or "")[:500],
            "url": f"https://openreview.net/forum?id={n.get('id')}",
        })
    return out
