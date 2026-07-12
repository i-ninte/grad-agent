"""Semantic Scholar client. Verifies faculty candidates and pulls recent papers.

v2 hardening:
  - Optional API key via S2_API_KEY env (x-api-key header, dedicated quota).
  - Exponential backoff on 429/5xx instead of a fixed 2s sleep.
  - On-disk cache of author lookups (data/s2_cache.json, 14 day TTL) so repeat
    candidates cost zero API calls.
  - Returns the canonical authorId, which the outreach log uses for dedup.
"""
from __future__ import annotations
import json
import os
import time

import httpx

from .. import config as _cfg

BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS_AUTHOR = "authorId,name,affiliations,hIndex,paperCount,homepage,url"
FIELDS_PAPERS = "title,abstract,year,venue,authors,externalIds"

CACHE_TTL = 14 * 24 * 3600  # 14 days


def _cache_path():
    return _cfg.data_dir() / "s2_cache.json"


def _cache_load() -> dict:
    p = _cache_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _cache_save(cache: dict) -> None:
    try:
        _cache_path().write_text(json.dumps(cache))
    except Exception:
        pass


def _cache_get(cache: dict, key: str):
    entry = cache.get(key)
    if not entry:
        return None
    if time.time() - entry.get("ts", 0) > CACHE_TTL:
        return None
    return entry.get("value")


def _cache_put(cache: dict, key: str, value) -> None:
    cache[key] = {"ts": time.time(), "value": value}


def _headers() -> dict:
    h = {"User-Agent": "grad-agent/0.1"}
    key = os.environ.get("S2_API_KEY", "").strip()
    if key:
        h["x-api-key"] = key
    return h


def _get(path: str, params: dict, max_retries: int = 5) -> dict | None:
    delay = 1.0
    for _ in range(max_retries):
        try:
            r = httpx.get(f"{BASE}{path}", params=params, timeout=30,
                          headers=_headers())
        except Exception:
            time.sleep(delay); delay = min(delay * 2, 30)
            continue
        if r.status_code == 200:
            return r.json()
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(delay); delay = min(delay * 2, 30)
            continue
        return None  # other 4xx: retrying will not help
    return None


def find_author(name: str) -> dict | None:
    """Best match by name. Prefers records with a positive h-index."""
    j = _get("/author/search", {"query": name, "fields": FIELDS_AUTHOR, "limit": 5})
    if not j:
        return None
    for a in j.get("data", []):
        if (a.get("hIndex") or 0) >= 1:
            return a
    return (j.get("data") or [None])[0]


def is_faculty(author: dict) -> tuple[bool, str]:
    """Heuristic: affiliation on record, h-index >= 6, paper count >= 12."""
    if not author:
        return False, "no author record"
    h = author.get("hIndex") or 0
    n = author.get("paperCount") or 0
    aff = author.get("affiliations") or []
    if not aff:
        return False, "no affiliation on record"
    if h < 6:
        return False, f"h-index {h} too low"
    if n < 12:
        return False, f"paper count {n} too low"
    return True, f"h={h} n={n} aff={aff[0]}"


def recent_papers(author_id: str, limit: int = 5) -> list[dict]:
    cache = _cache_load()
    key = f"papers:{author_id}:{limit}"
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    j = _get(f"/author/{author_id}/papers",
             {"fields": FIELDS_PAPERS, "limit": limit})
    if not j:
        return []
    out = []
    for p in j.get("data", []):
        if not p.get("abstract"):
            continue
        out.append({
            "title": p.get("title", ""),
            "abstract": p.get("abstract", "")[:1600],
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "url": (p.get("externalIds", {}) or {}).get("ArXiv"),
        })
    out.sort(key=lambda x: x.get("year") or 0, reverse=True)
    _cache_put(cache, key, out)
    _cache_save(cache)
    return out


def verify_by_name(name: str) -> dict:
    cache = _cache_load()
    key = f"verify:{name.strip().lower()}"
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    a = find_author(name)
    if not a:
        result = {"ok": False, "reason": "no match on semantic scholar",
                  "author_id": None}
    else:
        ok, reason = is_faculty(a)
        result = {
            "ok": ok, "reason": reason, "author_id": a.get("authorId"),
            "name": a.get("name"), "h_index": a.get("hIndex"),
            "paper_count": a.get("paperCount"),
            "affiliations": a.get("affiliations") or [],
            "homepage": a.get("homepage"),
            "s2_url": a.get("url"),
        }
    _cache_put(cache, key, result)
    _cache_save(cache)
    return result
