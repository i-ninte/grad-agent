"""DuckDuckGo HTML fallback for finding lab pages / funding info. No API key."""
from __future__ import annotations
import httpx
from bs4 import BeautifulSoup


def search(query: str, max_results: int = 10) -> list[dict]:
    r = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=30,
    )
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for res in soup.select("div.result")[:max_results]:
        a = res.select_one("a.result__a")
        snip = res.select_one("a.result__snippet")
        if not a:
            continue
        out.append({
            "title": a.get_text(strip=True),
            "url": a.get("href", ""),
            "snippet": snip.get_text(strip=True) if snip else "",
        })
    return out


def find_prof_page(name: str, university: str = "") -> list[dict]:
    return search(f'"{name}" {university} professor research')
