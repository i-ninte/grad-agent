"""Login to /admin-portal-k0 and POST a new blog post. Defaults to draft.

The portfolio's BlogContent component parses `content` as HTML (via DOMParser),
so we convert markdown drafts to HTML before POSTing. Code fences become
<pre><code class="language-x">, headings become <h1>..<h6>, etc.
"""
from __future__ import annotations
import os
import httpx
import markdown as md


_MD_EXTS = [
    "fenced_code",       # ```lang blocks
    "tables",            # pipe tables
    "sane_lists",
    "attr_list",
    "codehilite",        # adds language-x class on <code>
    "pymdownx.tilde",    # ~~strike~~
    "pymdownx.superfences",
]


def md_to_html(text: str) -> str:
    return md.markdown(text, extensions=_MD_EXTS, output_format="html5")


def _client() -> httpx.Client:
    return httpx.Client(base_url=os.environ["PORTFOLIO_BASE_URL"], timeout=30, follow_redirects=True)


def _login(c: httpx.Client) -> None:
    r = c.post(
        "/api/admin/login",
        json={"password": os.environ["PORTFOLIO_ADMIN_PASSWORD"]},
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()


def create_post(title: str, content: str, excerpt: str = "", publish: bool = False,
                cover_image: str | None = None, is_markdown: bool = True) -> dict:
    html = md_to_html(content) if is_markdown else content
    with _client() as c:
        _login(c)
        r = c.post(
            "/api/admin/posts",
            json={
                "title": title,
                "content": html,
                "excerpt": excerpt,
                "coverImage": cover_image,
                "published": publish,
                "categoryIds": [],
                "tagIds": [],
            },
            headers={"Content-Type": "application/json"},
        )
        r.raise_for_status()
        return {"status": r.status_code, "response": r.json() if r.text else {}}


def update_post(post_id: str, title: str | None = None, content: str | None = None,
                excerpt: str | None = None, publish: bool | None = None,
                is_markdown: bool = True) -> dict:
    payload: dict = {}
    if title is not None: payload["title"] = title
    if content is not None:
        payload["content"] = md_to_html(content) if is_markdown else content
    if excerpt is not None: payload["excerpt"] = excerpt
    if publish is not None: payload["published"] = publish
    with _client() as c:
        _login(c)
        r = c.put(f"/api/admin/posts/{post_id}", json=payload,
                  headers={"Content-Type": "application/json"})
        r.raise_for_status()
        return {"status": r.status_code, "response": r.json() if r.text else {}}


def delete_post(post_id: str) -> dict:
    with _client() as c:
        _login(c)
        r = c.delete(f"/api/admin/posts/{post_id}")
        r.raise_for_status()
        return {"status": r.status_code}


def list_posts() -> list[dict]:
    with _client() as c:
        _login(c)
        r = c.get("/api/admin/posts")
        r.raise_for_status()
        return r.json().get("posts", [])
