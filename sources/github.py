"""GitHub read: enumerate user repos + fetch README snippets."""
from __future__ import annotations
import os
import base64
import httpx


def _client() -> httpx.Client:
    h = {"Accept": "application/vnd.github+json",
         "X-GitHub-Api-Version": "2022-11-28"}
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok: h["Authorization"] = f"Bearer {tok}"
    return httpx.Client(base_url="https://api.github.com", headers=h, timeout=30)


def list_repos(username: str | None = None, include_private: bool = True) -> list[dict]:
    user = username or os.environ.get("GITHUB_USERNAME", "").strip()
    if not user: return []
    with _client() as c:
        # /user/repos returns private too when token is present; /users/{u}/repos only public
        endpoint = "/user/repos" if (include_private and os.environ.get("GITHUB_TOKEN")) else f"/users/{user}/repos"
        params = {"per_page": 100, "sort": "updated", "visibility": "all"} if endpoint == "/user/repos" else {"per_page": 100, "sort": "updated"}
        out = []
        page = 1
        while True:
            params["page"] = page
            r = c.get(endpoint, params=params)
            r.raise_for_status()
            batch = r.json()
            if not batch: break
            for repo in batch:
                # only keep owned repos when using /user/repos
                if repo.get("owner", {}).get("login", "").lower() != user.lower():
                    continue
                out.append({
                    "name": repo["name"],
                    "full_name": repo["full_name"],
                    "html_url": repo["html_url"],
                    "description": repo.get("description") or "",
                    "topics": repo.get("topics", []),
                    "language": repo.get("language") or "",
                    "stars": repo.get("stargazers_count", 0),
                    "updated_at": repo.get("updated_at", ""),
                    "private": repo.get("private", False),
                    "archived": repo.get("archived", False),
                    "fork": repo.get("fork", False),
                })
            page += 1
            if page > 5: break
        return out


def fetch_readme(full_name: str, max_chars: int = 4000) -> str:
    with _client() as c:
        r = c.get(f"/repos/{full_name}/readme")
        if r.status_code != 200: return ""
        data = r.json()
        if data.get("encoding") == "base64":
            try:
                return base64.b64decode(data.get("content", "")).decode("utf-8", "ignore")[:max_chars]
            except Exception:
                return ""
        return ""
