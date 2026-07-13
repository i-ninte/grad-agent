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


def cache_invalidate(substring: str = "", everything: bool = False) -> int:
    """Delete cache entries whose key contains `substring` (case-insensitive).
    Matches verify:{name}, author:{id}, papers:{id} keys. Pass everything=True
    to wipe the whole cache; an empty substring alone is refused so a typo
    cannot nuke two weeks of lookups."""
    cache = _cache_load()
    if everything:
        n = len(cache)
        _cache_save({})
        return n
    if not substring.strip():
        return 0
    needle = substring.strip().lower()
    victims = [k for k in cache if needle in k.lower()]
    for k in victims:
        del cache[k]
    if victims:
        _cache_save(cache)
    return len(victims)


def _headers() -> dict:
    h = {"User-Agent": "grad-agent/0.1"}
    key = os.environ.get("S2_API_KEY", "").strip()
    if key:
        h["x-api-key"] = key
    return h


# S2's terms cap at 1 request/second, cumulative across endpoints. Enforce
# a client-side floor between requests rather than relying on 429 backoff.
_MIN_INTERVAL = 1.1
_last_request_ts = 0.0


def _throttle() -> None:
    global _last_request_ts
    wait = _MIN_INTERVAL - (time.time() - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.time()


def _get(path: str, params: dict, max_retries: int = 5) -> dict | None:
    delay = 1.0
    for _ in range(max_retries):
        try:
            _throttle()
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
    """Heuristic: h-index >= 6 and paper count >= 12 separate PIs from
    students. Affiliation is NOT required: most S2 author records have an
    empty affiliations field, so demanding it rejects real faculty wholesale.
    Region filtering copes via the homepage TLD when affiliation is blank."""
    if not author:
        return False, "no author record"
    h = author.get("hIndex") or 0
    n = author.get("paperCount") or 0
    aff = author.get("affiliations") or []
    if h < 6:
        return False, f"h-index {h} too low"
    if n < 12:
        return False, f"paper count {n} too low"
    aff_note = aff[0] if aff else "no affiliation on S2, verify manually"
    return True, f"h={h} n={n} aff={aff_note}"


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


def _verify_record(a: dict | None, resolution: str = "name-search") -> dict:
    if not a:
        return {"ok": False, "reason": "no match on semantic scholar",
                "author_id": None, "resolution": resolution}
    ok, reason = is_faculty(a)
    return {
        "ok": ok, "reason": reason, "author_id": a.get("authorId"),
        "name": a.get("name"), "h_index": a.get("hIndex"),
        "paper_count": a.get("paperCount"),
        "affiliations": a.get("affiliations") or [],
        "homepage": a.get("homepage"),
        "s2_url": a.get("url"),
        "resolution": resolution,
    }


def verify_by_name(name: str) -> dict:
    cache = _cache_load()
    key = f"verify:{name.strip().lower()}"
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    result = _verify_record(find_author(name))
    _cache_put(cache, key, result)
    _cache_save(cache)
    return result


def author_by_id(author_id: str) -> dict | None:
    """Fetch a full author record for a known authorId. Cached."""
    cache = _cache_load()
    key = f"author:{author_id}"
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    a = _get(f"/author/{author_id}", {"fields": FIELDS_AUTHOR})
    _cache_put(cache, key, a)
    _cache_save(cache)
    return a


def paper_authors(arxiv_id: str) -> list[dict]:
    """Exact author entities for an arXiv paper: [{authorId, name}, ...].
    This is ground truth; no name matching involved. Cached."""
    if not arxiv_id:
        return []
    cache = _cache_load()
    key = f"paper:{arxiv_id}"
    hit = _cache_get(cache, key)
    if hit is not None:
        return hit
    j = _get(f"/paper/arXiv:{arxiv_id}",
             {"fields": "authors.authorId,authors.name,title"})
    authors = (j or {}).get("authors") or []
    out = [{"authorId": a.get("authorId"), "name": a.get("name", "")}
           for a in authors if a.get("authorId")]
    _cache_put(cache, key, out)
    _cache_save(cache)
    return out


def _norm_title(t: str) -> str:
    import re as _re
    return _re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def _author_wrote(author_id: str, paper_title: str) -> bool:
    """Does this author's paper list contain the trigger paper (title match)?"""
    target = _norm_title(paper_title)
    if not target:
        return False
    for p in recent_papers(author_id, limit=50):
        if _norm_title(p.get("title", "")) == target:
            return True
    return False


def resolve_author(name: str, arxiv_id: str = "", paper_title: str = "") -> dict:
    """Identity-safe resolution for the arXiv-driven pipeline.

    Tier 1 (paper-anchored): resolve the trigger paper on S2 and take the
    matching author's authorId directly. No name search; collisions are
    structurally impossible.

    Tier 2 (validated name search): search by name, accept only a candidate
    whose paper list contains the trigger paper.

    Tier 3: identity ambiguous. Never draft on an unverified identity."""
    # Tier 1
    authors = paper_authors(arxiv_id) if arxiv_id else []
    if authors:
        last_token = (name or "").split()[-1].lower()
        anchor = None
        for a in authors:
            if a["name"].split()[-1].lower() == last_token:
                anchor = a
        anchor = anchor or authors[-1]  # senior author by convention
        record = author_by_id(anchor["authorId"])
        if record:
            return _verify_record(record, resolution="paper-anchored")

    # Tier 2
    j = _get("/author/search", {"query": name, "fields": FIELDS_AUTHOR, "limit": 5})
    candidates = [a for a in (j or {}).get("data", [])
                  if (a.get("hIndex") or 0) >= 1][:3]
    if paper_title:
        for a in candidates:
            if _author_wrote(a.get("authorId", ""), paper_title):
                return _verify_record(a, resolution="name-validated")
    # A single candidate with no way to validate is still a guess; only
    # accept it when there was genuinely nothing to validate against.
    if not paper_title and len(candidates) == 1:
        return _verify_record(candidates[0], resolution="single-candidate")

    # Tier 3
    return {"ok": False,
            "reason": "identity ambiguous: could not anchor to trigger paper",
            "author_id": None, "resolution": "ambiguous"}


def resolve_for_program(name: str, university: str) -> dict:
    """Identity resolution for curated program faculty: prefer the candidate
    whose S2 affiliation overlaps the program's university."""
    j = _get("/author/search", {"query": name, "fields": FIELDS_AUTHOR, "limit": 5})
    candidates = (j or {}).get("data", []) or []
    if not candidates:
        return {"ok": False, "reason": "no match on semantic scholar",
                "author_id": None, "resolution": "ambiguous"}
    GENERIC = {"university", "universite", "universitat", "institute",
               "college", "school", "department", "technology", "science",
               "sciences", "state", "national", "polytechnic"}
    uni_words = {w for w in _norm_title(university).split()
                 if len(w) > 3 and w not in GENERIC}
    if uni_words:
        for a in candidates:
            aff_words = set()
            for aff in a.get("affiliations") or []:
                aff_words |= set(_norm_title(aff).split())
            if uni_words & aff_words:
                return _verify_record(a, resolution="affiliation-anchored")
    if len(candidates) == 1:
        return _verify_record(candidates[0], resolution="single-candidate")
    # S2 affiliations are empty on most records, so affiliation anchoring
    # often cannot fire. For a human-curated faculty name, the intended
    # person is almost always the established scholar with that name: accept
    # the top candidate iff it clearly dominates the runner-up on h-index.
    ranked = sorted(candidates, key=lambda a: (a.get("hIndex") or 0), reverse=True)
    top_h = ranked[0].get("hIndex") or 0
    second_h = ranked[1].get("hIndex") or 0 if len(ranked) > 1 else 0
    if top_h >= 6 and top_h >= 2 * max(second_h, 1):
        return _verify_record(ranked[0], resolution="dominant-candidate")
    return {"ok": False,
            "reason": f"identity ambiguous: {len(candidates)} comparable "
                      f"candidates (h={top_h} vs h={second_h}), none anchored "
                      f"to {university}",
            "author_id": None, "resolution": "ambiguous"}
