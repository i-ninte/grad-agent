"""Extend the project catalog from GitHub + HuggingFace + local NINTE dirs.

Writes/updates `catalog.json` in the grad-agent directory. Each entry has the
same shape as the seed `PROJECTS` list in projects.py:
    {name, pitch, link, tags}
Claude Haiku distils each source (repo, model, local README) into the pitch
and tags. Existing entries are updated in place; new ones appended.
"""
from __future__ import annotations
import os, json, re, time
from pathlib import Path

from . import config as _cfg
_cfg.load_env_file()

from .sources import github as gh
from .sources import hf

try:
    import anthropic
except Exception:
    anthropic = None


def _catalog_path() -> Path:
    return _cfg.data_dir() / "catalog.json"


def _projects_dir() -> Path:
    prof = _cfg.load_profile()
    if prof.projects_dir:
        return Path(prof.projects_dir).expanduser()
    return Path(os.environ.get("NINTE_ROOT", str(Path.home())))

# Skip these local dirs when scanning _projects_dir()
SKIP_LOCAL = {"GRAD", "portfolio", "SNAPSHOT", "Kwabena.zip"}

SYSTEM = (
    "You extract a compact JSON record from a project description. Return a "
    "strict JSON object with keys: pitch (one sentence, 25 to 45 words, in "
    "Kwabena's voice, direct and grounded in the actual work described, no "
    "cliches, no dashes), tags (a list of 5 to 12 short lowercase phrases "
    "describing the technical area, methods, and domain, e.g. 'nlp', 'llm', "
    "'african languages', 'yolo', 'time series'). Nothing else. No prose "
    "outside the JSON."
)


def _distil(name: str, kind: str, description: str, extra: str = "",
            model: str = "claude-haiku-4-5-20251001") -> dict:
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        # Heuristic: pitch = first 40 words of description, tags = topics/tags
        pitch = " ".join((description or f"{kind} named {name}").split()[:40])
        return {"pitch": pitch, "tags": []}
    client = anthropic.Anthropic()
    user = (
        f"KIND: {kind}\nNAME: {name}\nDESCRIPTION: {description}\n\n"
        f"EXTRA CONTEXT (README or metadata):\n{extra[:3000]}\n\n"
        f"Return the JSON now."
    )
    m = client.messages.create(
        model=model, max_tokens=400, system=SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    raw = m.content[0].text.strip()
    # tolerate ```json fences
    raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()
    try:
        obj = json.loads(raw)
        obj["pitch"] = obj.get("pitch", "").replace("—", ", ").replace("–", ", ")
        return {"pitch": obj.get("pitch", ""), "tags": obj.get("tags", []) or []}
    except Exception:
        return {"pitch": (description or "")[:200], "tags": []}


def _load() -> dict:
    if _catalog_path().exists():
        return json.loads(_catalog_path().read_text())
    return {"projects": {}, "last_synced": None}


def _save(cat: dict) -> None:
    cat["last_synced"] = time.strftime("%Y-%m-%d %H:%M")
    _catalog_path().write_text(json.dumps(cat, indent=2))


def _upsert(cat: dict, key: str, entry: dict) -> None:
    cat["projects"][key] = entry


def sync_github() -> int:
    cat = _load(); added = 0
    for r in gh.list_repos():
        if r["fork"] or r["archived"]: continue
        readme = gh.fetch_readme(r["full_name"])
        d = _distil(
            name=r["name"],
            kind="github repo",
            description=r["description"] or "",
            extra=(readme or "") + "\nTopics: " + ", ".join(r["topics"]),
        )
        entry = {
            "name": r["name"],
            "pitch": d["pitch"] or (r["description"] or r["name"]),
            "link": r["html_url"],
            "tags": list(dict.fromkeys(d["tags"] + r["topics"])),
            "source": "github",
            "language": r["language"],
            "stars": r["stars"],
        }
        _upsert(cat, f"gh:{r['full_name']}", entry); added += 1
    _save(cat); return added


def sync_hf() -> int:
    cat = _load(); added = 0
    for m in hf.list_models() + hf.list_datasets():
        readme = hf.fetch_readme(m["id"], kind=m["kind"] + "s")
        d = _distil(
            name=m["id"],
            kind=f"huggingface {m['kind']}",
            description=(m.get("pipeline_tag") or "") + " " + ", ".join(m["tags"][:10]),
            extra=readme,
        )
        entry = {
            "name": m["id"],
            "pitch": d["pitch"] or f"{m['kind']} at {m['id']}",
            "link": m["url"],
            "tags": list(dict.fromkeys(d["tags"] + m["tags"])),
            "source": "huggingface",
            "downloads": m["downloads"],
            "likes": m["likes"],
        }
        _upsert(cat, f"hf:{m['kind']}:{m['id']}", entry); added += 1
    _save(cat); return added


def sync_local() -> int:
    cat = _load(); added = 0
    for child in _projects_dir().iterdir():
        if not child.is_dir() or child.name in SKIP_LOCAL: continue
        readme_text = ""
        for cand in ("README.md", "Readme.md", "readme.md", "README.txt"):
            p = child / cand
            if p.exists():
                readme_text = p.read_text(errors="ignore")[:4000]; break
        if not readme_text and not any((child / c).exists() for c in ("package.json", "requirements.txt")):
            continue
        d = _distil(
            name=child.name, kind="local project directory",
            description="", extra=readme_text,
        )
        entry = {
            "name": child.name,
            "pitch": d["pitch"] or child.name,
            "link": str(child),
            "tags": d["tags"],
            "source": "local",
        }
        _upsert(cat, f"local:{child.name}", entry); added += 1
    _save(cat); return added


def sync_all() -> dict:
    return {
        "github": sync_github(),
        "huggingface": sync_hf(),
        "local": sync_local(),
        "catalog_path": str(_catalog_path()),
    }


if __name__ == "__main__":
    print(sync_all())
