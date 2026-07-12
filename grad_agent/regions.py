"""Map a university affiliation string to a country/region.

Keyword table first (fast, offline, covers the common cases), Claude Haiku
fallback for unknowns when an API key is present. Unknowns are NEVER silently
dropped by the caller: daily_run keeps them and flags them for manual check,
because a false negative (skipping a great US prof whose affiliation string
we failed to parse) costs more than one extra line in the review email.
"""
from __future__ import annotations
import json
import os
import re

# Region name -> lowercase keywords matched against the affiliation string.
KEYWORDS: dict[str, list[str]] = {
    "US": [
        "united states", "usa", " mit", "massachusetts", "stanford", "berkeley",
        "carnegie mellon", "cmu", "harvard", "princeton", "cornell", "columbia",
        "yale", "caltech", "georgia tech", "georgia institute", "university of washington",
        "michigan", "wisconsin", "illinois", "urbana", "austin", "texas",
        "ucla", "ucsd", "uc san", "uc davis", "uc irvine", "usc", "nyu",
        "new york university", "johns hopkins", "duke", "north carolina",
        "maryland", "pennsylvania", "upenn", "purdue", "ohio state",
        "minnesota", "colorado", "arizona", "florida", "virginia",
        "northwestern", "brown university", "rice university", "vanderbilt",
        "notre dame", "boston university", "northeastern", "stony brook",
        "rutgers", "penn state", "indiana university", "pittsburgh",
        "amherst", "california",
    ],
    "Canada": [
        "canada", "toronto", "mcgill", "mila", "waterloo", "british columbia",
        "ubc", "montreal", "montréal", "alberta", "mcmaster", "simon fraser",
        "ottawa", "queen's university", "york university", "vector institute",
        "laval", "manitoba", "saskatchewan", "dalhousie", "calgary",
    ],
    "UK": [
        "united kingdom", " uk", "oxford", "cambridge", "imperial college",
        "edinburgh", "ucl", "university college london", "king's college",
        "manchester", "sheffield", "bristol", "warwick", "glasgow",
        "southampton", "leeds", "birmingham", "nottingham", "queen mary",
        "alan turing institute", "deepmind",
    ],
    "EU": [
        "germany", "france", "netherlands", "switzerland", "sweden", "denmark",
        "italy", "spain", "austria", "belgium", "finland", "norway", "poland",
        "portugal", "ireland", "eth zurich", "eth zürich", "epfl",
        "max planck", "tu munich", "tu münchen", "lmu", "saarland",
        "amsterdam", "delft", "leuven", "kth", "aalto", "inria", "sorbonne",
        "université", "universität", "universidad", "università", "romania",
        "bucharest", "czech", "greece", "hungary", "lorraine",
    ],
    "Asia": [
        "china", "tsinghua", "peking", "shanghai", "zhejiang", "fudan",
        "hong kong", "hkust", "japan", "tokyo", "kyoto", "korea", "kaist",
        "seoul", "singapore", " nus ", "nanyang", "india", " iit ", "iisc",
        "taiwan", "israel", "technion", "tel aviv", "weizmann",
        "saudi", "kaust", "uae", "mbzuai", "qatar",
    ],
    "Africa": [
        "south africa", "cape town", "witwatersrand", "stellenbosch",
        "ghana", "knust", "legon", "nigeria", "lagos", "ibadan", "kenya",
        "nairobi", "egypt", "cairo", "morocco", "tunisia", "rwanda",
        "aims", "ethiopia", "makerere", "uganda",
    ],
    "Australia": [
        "australia", "melbourne", "sydney", "monash", " anu ",
        "queensland", "adelaide", "new zealand", "auckland",
    ],
}

# Countries commonly used as region aliases in profile.yaml.
ALIASES = {
    "usa": "US", "united states": "US", "america": "US",
    "britain": "UK", "england": "UK", "united kingdom": "UK",
    "europe": "EU",
}


# Country-code TLD -> region. Applied to the prof's homepage URL, which we
# already have from Semantic Scholar, before falling back to the LLM.
TLD_REGIONS = {
    ".edu": "US", ".gov": "US",
    ".ca": "Canada",
    ".ac.uk": "UK", ".co.uk": "UK",
    ".de": "EU", ".fr": "EU", ".nl": "EU", ".ch": "EU", ".se": "EU",
    ".dk": "EU", ".it": "EU", ".es": "EU", ".at": "EU", ".be": "EU",
    ".fi": "EU", ".no": "EU", ".pl": "EU", ".pt": "EU", ".ie": "EU",
    ".ro": "EU", ".cz": "EU", ".gr": "EU", ".hu": "EU",
    ".cn": "Asia", ".jp": "Asia", ".kr": "Asia", ".sg": "Asia",
    ".hk": "Asia", ".tw": "Asia", ".in": "Asia", ".il": "Asia",
    ".ae": "Asia", ".sa": "Asia", ".qa": "Asia",
    ".za": "Africa", ".gh": "Africa", ".ng": "Africa", ".ke": "Africa",
    ".eg": "Africa", ".ma": "Africa", ".tn": "Africa", ".rw": "Africa",
    ".ug": "Africa", ".et": "Africa",
    ".au": "Australia", ".nz": "Australia",
}


def normalise_region(r: str) -> str:
    return ALIASES.get(r.strip().lower(), r.strip())


def _from_tld(homepage: str) -> str:
    """Infer region from the host of a homepage URL. '' if no signal."""
    if not homepage:
        return ""
    m = re.search(r"https?://([^/\s]+)", homepage.strip())
    host = (m.group(1) if m else homepage.strip()).lower().rstrip(".")
    # Longest suffix first so .ac.uk beats .uk-style false positives.
    for tld in sorted(TLD_REGIONS, key=len, reverse=True):
        if host.endswith(tld):
            return TLD_REGIONS[tld]
    return ""


def _region_cache_path():
    from . import config as _cfg
    return _cfg.data_dir() / "region_cache.json"


def _cache_read() -> dict:
    p = _region_cache_path()
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def _cache_write(cache: dict) -> None:
    try:
        _region_cache_path().write_text(json.dumps(cache))
    except Exception:
        pass


def infer(affiliation: str, homepage: str = "") -> str:
    """Region from keyword table, then homepage TLD, then cached LLM fallback."""
    if not affiliation and not homepage:
        return "unknown"
    s = " " + (affiliation or "").lower() + " "
    for region, words in KEYWORDS.items():
        for w in words:
            if w in s:
                return region
    tld = _from_tld(homepage)
    if tld:
        return tld
    if not affiliation:
        return "unknown"
    cache = _cache_read()
    key = affiliation.strip().lower()
    if key in cache:
        return cache[key]
    region = _infer_llm(affiliation)
    if region != "unknown":
        cache[key] = region
        _cache_write(cache)
    return region


def _infer_llm(affiliation: str) -> str:
    """Haiku fallback for affiliations the keyword table misses."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "unknown"
    try:
        import anthropic
        client = anthropic.Anthropic()
        m = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=30,
            system=(
                "Classify the university affiliation into exactly one region: "
                "US, Canada, UK, EU, Asia, Africa, Australia, or unknown. "
                "Reply with the single region token only."
            ),
            messages=[{"role": "user", "content": affiliation}],
        )
        token = m.content[0].text.strip().split()[0]
        return token if token in (*KEYWORDS.keys(), "unknown") else "unknown"
    except Exception:
        return "unknown"


def allowed(affiliation: str, target_regions: list[str],
            homepage: str = "") -> tuple[bool, str]:
    """Return (allowed, inferred_region). Empty target list allows everything.
    Unknown regions are allowed but flagged, never silently dropped."""
    if not target_regions:
        return True, infer(affiliation, homepage)
    targets = {normalise_region(r) for r in target_regions}
    region = infer(affiliation, homepage)
    if region == "unknown":
        return True, "unknown"
    return region in targets, region
