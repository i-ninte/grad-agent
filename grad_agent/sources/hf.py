"""HuggingFace read: enumerate a user's published models + datasets."""
from __future__ import annotations
import os
import httpx


def _client() -> httpx.Client:
    h = {"Accept": "application/json"}
    tok = os.environ.get("HF_TOKEN", "").strip()
    if tok: h["Authorization"] = f"Bearer {tok}"
    return httpx.Client(base_url="https://huggingface.co", headers=h, timeout=30)


def _list(kind: str, author: str) -> list[dict]:
    with _client() as c:
        r = c.get(f"/api/{kind}", params={"author": author, "limit": 200, "full": "true"})
        if r.status_code != 200: return []
        out = []
        for m in r.json():
            out.append({
                "id": m.get("id") or m.get("modelId") or "",
                "url": f"https://huggingface.co/{m.get('id', '')}" if kind == "models" else f"https://huggingface.co/datasets/{m.get('id','')}",
                "tags": m.get("tags", []),
                "pipeline_tag": m.get("pipeline_tag") or m.get("task") or "",
                "downloads": m.get("downloads", 0),
                "likes": m.get("likes", 0),
                "kind": kind[:-1],
            })
        return out


def list_models(author: str | None = None) -> list[dict]:
    a = author or os.environ.get("HF_USERNAME", "").strip()
    if not a: return []
    return _list("models", a)


def list_datasets(author: str | None = None) -> list[dict]:
    a = author or os.environ.get("HF_USERNAME", "").strip()
    if not a: return []
    return _list("datasets", a)


def fetch_readme(repo_id: str, kind: str = "models", max_chars: int = 4000) -> str:
    with _client() as c:
        prefix = "" if kind == "models" else "datasets/"
        r = c.get(f"/{prefix}{repo_id}/raw/main/README.md")
        if r.status_code != 200: return ""
        return r.text[:max_chars]
