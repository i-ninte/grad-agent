"""Detect whether a professor's lab page signals active grad-student recruiting.
Looks at homepage plus a few common subpages. Also extracts any .edu email."""
from __future__ import annotations
import httpx, re
from bs4 import BeautifulSoup


PHRASES = [
    r"prospective\s+students?", r"looking\s+for\s+(?:phd|graduate|ms|msc)",
    r"recruiting", r"openings?\s+for\s+(?:phd|graduate)",
    r"i\s+am\s+accepting\s+(?:phd|graduate|new)", r"apply\s+to\s+work\s+with",
    r"if\s+you\s+are\s+interested\s+in\s+joining",
    r"currently\s+seeking", r"positions\s+available",
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _fetch(url: str) -> str:
    try:
        r = httpx.get(url, timeout=20, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200: return ""
        return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)
    except Exception:
        return ""


def signal(homepage: str) -> dict:
    if not homepage: return {"recruiting": None, "matched": [], "email": None, "page_text": ""}
    texts: list[str] = []
    urls = [homepage]
    for tail in ("/prospective", "/students", "/openings", "/join", "/join-us"):
        urls.append(homepage.rstrip("/") + tail)
    for u in urls:
        t = _fetch(u)
        if t: texts.append(t)
    corpus = " ".join(texts).lower()
    matched = [p for p in PHRASES if re.search(p, corpus)]
    emails = EMAIL_RE.findall(" ".join(texts))
    # prefer .edu addresses
    edu = next((e for e in emails if e.lower().endswith(".edu")), None)
    return {"recruiting": bool(matched), "matched": matched[:3],
            "email": edu or (emails[0] if emails else None),
            # first chunk of the homepage itself, for affiliation freshness checks
            "page_text": (texts[0] if texts else "")[:2000]}
