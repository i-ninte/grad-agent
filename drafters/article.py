"""Blog article drafter. Markdown-with-LaTeX-math for portfolio.
Reads a project dir under NINTE_ROOT, produces a technical post.
"""
from __future__ import annotations
import os
from pathlib import Path


def scan_project(project_name: str, ninte_root: str) -> dict:
    root = Path(ninte_root) / project_name
    if not root.exists():
        return {"error": f"project not found: {root}"}
    readme = ""
    for cand in ["README.md", "readme.md", "README.txt"]:
        f = root / cand
        if f.exists():
            readme = f.read_text(errors="ignore")[:8000]
            break
    files = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".js", ".sol", ".md"}:
            rel = p.relative_to(root)
            if any(x in str(rel) for x in ["node_modules", ".next", "dist", "build"]):
                continue
            files.append(str(rel))
            if len(files) >= 50:
                break
    return {"root": str(root), "readme": readme, "files": files}


def draft(project_name: str, ninte_root: str, angle: str = "engineering deep-dive") -> dict:
    info = scan_project(project_name, ninte_root)
    if "error" in info:
        return info
    title = f"{project_name}: {angle}"
    content = (
        f"# {title}\n\n"
        f"_Draft — review before publishing._\n\n"
        f"## What it is\n\n"
        f"{project_name} is a project in my NINTE workspace. Repo layout has "
        f"{len(info['files'])} source files.\n\n"
        f"## Why I built it\n\n"
        f"<!-- fill: motivation, the specific problem, why existing tools fell short -->\n\n"
        f"## How it works\n\n"
        f"<!-- fill: architecture, key algorithms. Use $LaTeX$ math where useful. -->\n\n"
        f"## README excerpt\n\n"
        f"```\n{info['readme'][:2000]}\n```\n\n"
        f"## What I would change\n\n"
        f"<!-- fill: known limits, next steps -->\n"
    )
    excerpt = f"Engineering notes on {project_name}."
    return {
        "title": title,
        "excerpt": excerpt,
        "content": content,
        "project_files": info["files"][:20],
    }
