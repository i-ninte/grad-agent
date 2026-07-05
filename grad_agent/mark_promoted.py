"""Mark high-signal catalog entries as promote:true.

Promoted by default: every HF publication and any local/github repo whose
name matches profile.seed_projects. Everything else defaults to False.
"""
from __future__ import annotations
import json

from . import config as _cfg


def run() -> dict:
    path = _cfg.data_dir() / "catalog.json"
    if not path.exists():
        return {"error": "no catalog to promote"}
    data = json.loads(path.read_text())
    prof = _cfg.load_profile()
    flagship = {(p.get("name") or "").lower() for p in prof.seed_projects}
    projects = data.get("projects", {})
    promoted = 0
    for _, p in projects.items():
        name = (p.get("name") or "").lower()
        if p.get("source") == "huggingface" or name in flagship:
            p["promote"] = True; promoted += 1
        else:
            p.setdefault("promote", False)
    path.write_text(json.dumps(data, indent=2))
    return {"promoted": promoted, "total": len(projects)}


if __name__ == "__main__":
    print(run())
