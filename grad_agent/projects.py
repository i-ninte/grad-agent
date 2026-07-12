"""Catalog of Kwabena's shippable work + a scorer that picks the strongest
match for a given professor's paper abstract.

Each entry is what a cold email can *credibly* stand on. Every project has:
  - name, one-line pitch (used in the email)
  - link (portfolio or github)
  - tags: area keywords for matching
"""
from __future__ import annotations
import json
import re

from . import config as _cfg


def _catalog_path():
    return _cfg.data_dir() / "catalog.json"


def _load_catalog_extras() -> list[dict]:
    p = _catalog_path()
    if not p.exists(): return []
    try:
        data = json.loads(p.read_text())
        return list(data.get("projects", {}).values())
    except Exception:
        return []


def _profile_seed() -> list[dict]:
    """seed_projects from the user's profile.yaml take precedence over the
    hardcoded fallback below (which is Kwabena's — kept only for backward
    compatibility during the migration)."""
    try:
        return _cfg.load_profile().seed_projects or []
    except Exception:
        return []


# Fallback seed for the original single-user setup. Empty for a fresh install.
_LEGACY_SEED: list[dict] = [
    {
        "name": "Kenya Clinical Reasoning Challenge (Zindi silver)",
        "pitch": "silver medal on Zindi's Kenya Clinical Reasoning Challenge, replicating clinician decision making from 400 authentic rural prompts using LoRA adapted Flan-T5 under severe class imbalance",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["nlp", "llm", "clinical", "health", "medical", "reasoning", "low resource", "african", "class imbalance", "lora", "flan", "medical nlp"],
    },
    {
        "name": "SUA Outsmarting Outbreaks Challenge (Zindi silver)",
        "pitch": "silver medal on Zindi's SUA Outsmarting Outbreaks Challenge, multimodal forecasting of climate sensitive waterborne disease outbreaks in Tanzania across 2019 to 2023, fusing time series health, climate, water quality, and sanitation data",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["multimodal", "health", "climate", "time series", "forecasting", "african", "public health", "epidemiology", "fusion", "tabular"],
    },
    {
        "name": "Ghana Crop Disease Detection Challenge (Zindi bronze)",
        "pitch": "bronze medal on Zindi's Ghana Crop Disease Detection Challenge, fine tuning YOLOv11 with stratified sampling under severe class imbalance while optimising for inference speed and memory",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["cv", "computer vision", "yolo", "detection", "agriculture", "class imbalance", "edge", "efficient", "african", "crop", "plant"],
    },
    {
        "name": "GeoForest",
        "pitch": "a Sentinel-2 satellite ML pipeline built at Ecoscan AI, pairing NDVI vegetation indices with RF-DETR object detection for near real time monitoring of deforestation and illegal mining (galamsey) in Ghana",
        "link": "https://i-ninte.vercel.app/blog/geoforest-satellite-monitoring-of-deforestation-and-galamsey-in-ghana",
        "tags": ["cv", "geospatial", "remote sensing", "satellite", "sentinel", "environment", "deforestation", "detr", "detection", "ndvi", "climate", "sustainability", "african"],
    },
    {
        "name": "Phrontlyne Claims Agent v2",
        "pitch": "a production autonomous insurance claims agent (currently in production at Phrontlyne Technologies), integrating a Claude driven MCP tool layer over 45 tools, two YOLO detectors composed by IoU geometry, and a four signal composite fraud pipeline, reducing manual processing by 40 percent and improving fraud validation by 45 percent",
        "link": "https://i-ninte.vercel.app/blog/building-an-autonomous-insurance-claims-agent-composite-vision-fraud-detection-and-mcp-tool-orchestration",
        "tags": ["agents", "llm", "tool use", "mcp", "cv", "yolo", "fraud", "multimodal", "production", "rag", "vision language", "composite", "orchestration"],
    },
    {
        "name": "deriv-rag",
        "pitch": "a retrieval augmented pipeline with citation validation and numeric grounding checks that flags rather than corrects hallucinations, built for a Deriv.com technical interview",
        "link": "https://i-ninte.vercel.app/blog/building-a-grounded-rag-pipeline-for-a-derivcom-technical-interview",
        "tags": ["nlp", "llm", "rag", "retrieval", "faiss", "grounding", "hallucination", "citation", "evaluation", "safety"],
    },
    {
        "name": "GhanaNLP-data-models-play",
        "pitch": "an early Ghanaian language data collection and model training effort focused on Twi and other underrepresented Ghanaian languages",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["nlp", "african", "low resource", "multilingual", "twi", "ghanaian", "language resource", "dataset", "african languages"],
    },
    {
        "name": "Aquamind (KNUST undergraduate thesis)",
        "pitch": "undergraduate thesis at KNUST, deploying LSTM and gradient boosting on an ESP32 IoT system for real time water quality prediction at 96 percent accuracy, designed so field operators could contest predictions rather than accept them blindly",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["time series", "iot", "embedded", "efficient", "edge", "water", "environment", "explainable", "lstm", "gradient boosting", "sensor"],
    },
    {
        "name": "AI Mentor at Dev2win",
        "pitch": "fine tuned Mistral for a mentor mentee AI mentor system, plus a cosine similarity matching algorithm that lifted matching accuracy 30 percent and engagement 20 percent",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["nlp", "llm", "fine tuning", "mistral", "lora", "recommendation", "similarity", "personalisation"],
    },
    {
        "name": "Sikasense ML pipeline for Ghana Enterprise Agency",
        "pitch": "end to end ML pipeline analysing 109000 female applicant profiles across four Mastercard funded programs, using logistic regression, random forest, and gradient boosting for eligibility and 28 feature viability and resilience prediction",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["ml", "tabular", "classification", "fairness", "social good", "development", "african", "policy"],
    },
    {
        "name": "AIDRE research assistantship on CCTV and behaviour in Ghana",
        "pitch": "nine month research assistantship at the African Institute for Development Research and Evaluation, designing survey instruments and analysing Ghana Police Service conviction data for a study on CCTV cameras and behavioural change",
        "link": "https://i-ninte.github.io/portfolio/",
        "tags": ["ethics", "policy", "surveillance", "bias", "human centered", "evaluation", "survey", "african", "governance"],
    },
]


def _all_projects() -> list[dict]:
    """profile.seed_projects, then legacy seed, then catalog. Dedup by name.
    profile seeds win. Legacy seed is only used if profile has none."""
    seen: dict[str, dict] = {}
    prof_seed = _profile_seed()
    ordered = prof_seed + (_LEGACY_SEED if not prof_seed else []) + _load_catalog_extras()
    for p in ordered:
        key = (p.get("name") or "").strip().lower()
        if not key or not p.get("pitch"): continue
        seen.setdefault(key, p)
    return list(seen.values())


PROJECTS = _all_projects()  # kept for external callers


def _tokens(text: str) -> set[str]:
    return set(w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 2)


# ── TF-IDF semantic layer ─────────────────────────────────────────────
# Pure-python cosine similarity between the paper text and each project's
# document (name + pitch + tags). Catches matches the tag table misses and
# penalises spurious single-tag overlaps, without adding an embedding API.

def _tf(text: str) -> dict[str, float]:
    words = [w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) > 2]
    if not words:
        return {}
    counts: dict[str, int] = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    total = len(words)
    return {w: c / total for w, c in counts.items()}


def _project_doc(p: dict) -> str:
    return " ".join([p.get("name", ""), p.get("pitch", ""),
                     " ".join(p.get("tags", []))])


def _idf(project_docs: list[str]) -> dict[str, float]:
    import math
    n = len(project_docs) or 1
    df: dict[str, int] = {}
    for doc in project_docs:
        for w in set(re.findall(r"[a-z]+", doc.lower())):
            if len(w) > 2:
                df[w] = df.get(w, 0) + 1
    return {w: math.log((n + 1) / (c + 1)) + 1 for w, c in df.items()}


def _cosine(tf_a: dict[str, float], tf_b: dict[str, float],
            idf: dict[str, float]) -> float:
    import math
    va = {w: f * idf.get(w, 1.0) for w, f in tf_a.items()}
    vb = {w: f * idf.get(w, 1.0) for w, f in tf_b.items()}
    dot = sum(va[w] * vb[w] for w in va.keys() & vb.keys())
    na = math.sqrt(sum(x * x for x in va.values()))
    nb = math.sqrt(sum(x * x for x in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def rank_projects(prof_paper_title: str, prof_paper_abstract: str, area: str = "",
                  top_k: int = 3, outcome_boost: dict[str, int] | None = None) -> list[dict]:
    """Return the top_k projects most relevant to this prof, scored by tag overlap
    with the paper's title, abstract, and the area label. Each result carries a
    `score` and `matched_tags` field for auditability.

    outcome_boost maps project name -> extra score, derived from tagged
    response outcomes in the outreach log (projects that got replies rank up)."""
    surface = " ".join([prof_paper_title or "", prof_paper_abstract or "", area or ""]).lower()
    surface_tokens = _tokens(surface)
    ranked = []
    # source prior: curated seed and HF published models beat throwaway repos
    SRC_PRIOR = {None: 3, "huggingface": 2, "local": 1, "github": 0}
    all_p = _all_projects()
    any_promoted = any(p.get("promote") for p in all_p)
    scorable = [p for p in all_p
                if not (any_promoted and not p.get("promote") and p.get("source"))]

    # TF-IDF prep over the scorable pool
    docs = [_project_doc(p) for p in scorable]
    idf = _idf(docs)
    query_tf = _tf(surface)

    for p, doc in zip(scorable, docs):
        matched = [t for t in p["tags"] if any(w in surface for w in t.split())]
        phrase_hits = sum(1 for t in p["tags"] if t in surface)
        token_hits = len(set(w for t in p["tags"] for w in t.split()) & surface_tokens)
        prior = SRC_PRIOR.get(p.get("source"), 0)
        depth_penalty = 0 if len(p.get("tags", [])) >= 5 else -2
        promote_bonus = 3 if p.get("promote") else 0
        learned = (outcome_boost or {}).get(p.get("name", ""), 0)
        semantic = round(8 * _cosine(query_tf, _tf(doc), idf))
        score = (3 * phrase_hits + token_hits + prior + depth_penalty
                 + promote_bonus + learned + semantic)
        ranked.append({**p, "score": score, "matched_tags": matched,
                       "outcome_boost": learned, "semantic_score": semantic})
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked[:top_k]


def best_project(prof_paper_title: str, prof_paper_abstract: str, area: str = "",
                 outcome_boost: dict[str, int] | None = None) -> dict:
    top = rank_projects(prof_paper_title, prof_paper_abstract, area, top_k=1,
                        outcome_boost=outcome_boost)
    return top[0] if top else _all_projects()[0]
