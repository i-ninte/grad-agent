"""arXiv search — recent papers by area, extract authors as prof candidates."""
from __future__ import annotations
import httpx
import feedparser
from urllib.parse import quote


AREA_QUERIES = {
    "nlp": "cat:cs.CL AND (abs:LLM OR abs:agent OR abs:alignment)",
    "llm": "cat:cs.CL AND abs:large language model",
    "ml": "cat:cs.LG",
    "cv": "cat:cs.CV",
    "ai4health": '(abs:"clinical" OR abs:"medical" OR abs:"health") AND cat:cs.LG',
    "africa": 'abs:"low resource" OR abs:"African"',
}


def search(area: str, max_results: int = 25) -> list[dict]:
    q = AREA_QUERIES.get(area, area)
    url = (
        f"https://export.arxiv.org/api/query?search_query={quote(q)}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )
    r = httpx.get(url, timeout=30)
    feed = feedparser.parse(r.text)
    out = []
    for e in feed.entries:
        out.append({
            "title": e.title.strip().replace("\n", " "),
            "authors": [a.name for a in getattr(e, "authors", [])],
            "abstract": e.summary.strip().replace("\n", " ")[:500],
            "url": e.link,
            "published": getattr(e, "published", ""),
        })
    return out
