"""One-shot: mark high-signal catalog entries as promote:true so the matcher
never surfaces throwaway repos (odin_project, sql_with_bigquery, etc.).

Promoted by default: seed projects, all HF publications, and a curated list
of local + github flagship repos.
"""
from __future__ import annotations
import json
from pathlib import Path

CATALOG = Path(__file__).parent / "catalog.json"

FLAGSHIP_LOCAL = {
    "ecoscan", "geoforest", "GhanaNLP-data-models-play", "PhrontlyneBaseTrain",
    "queryamie-mongo", "deriv-rag", "credit-unions", "RAIL",
}
FLAGSHIP_GH = {"i-ninte/deriv-rag", "i-ninte/geoforest", "i-ninte/ecoscan",
               "i-ninte/GhanaNLP-data-models-play", "i-ninte/QueryAmie"}
DEMOTED_KEYWORDS = {"odin", "sql_with_biq", "learning-", "ATS", "hello-world"}


def run():
    if not CATALOG.exists():
        print("no catalog to promote"); return
    data = json.loads(CATALOG.read_text())
    projects = data.get("projects", {})
    promoted = 0; demoted = 0
    for key, p in projects.items():
        src = p.get("source")
        name = (p.get("name") or "").lower()
        if src == "huggingface":
            p["promote"] = True; promoted += 1
        elif src == "local" and any(f.lower() in name for f in FLAGSHIP_LOCAL):
            p["promote"] = True; promoted += 1
        elif src == "github" and (p.get("full_name") in FLAGSHIP_GH or
                                  any(f.split("/")[1].lower() in name for f in FLAGSHIP_GH)):
            p["promote"] = True; promoted += 1
        elif any(bad in name for bad in DEMOTED_KEYWORDS):
            p["promote"] = False; demoted += 1
        else:
            p.setdefault("promote", False)
    CATALOG.write_text(json.dumps(data, indent=2))
    print(f"promoted={promoted} demoted={demoted} total={len(projects)}")


if __name__ == "__main__":
    run()
