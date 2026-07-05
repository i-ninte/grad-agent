"""Centralised config + paths + profile loader for grad-agent.

User data location (in priority order):
  1. $GRAD_AGENT_HOME
  2. ~/.grad-agent/
  3. Current working directory (for legacy/dev)

Layout under HOME:
  profile.yaml     user identity + preferences
  programs.yaml    user's target programs (seeded from template on init)
  .env             secrets only (SMTP, ANTHROPIC_API_KEY, GITHUB_TOKEN, ...)
  data/            outreach_log.xlsx, lor_log.xlsx, catalog.json, db.sqlite
  drafts/          per-school drafts
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None


PACKAGE_ROOT = Path(__file__).parent
TEMPLATES = PACKAGE_ROOT / "templates"


def home() -> Path:
    env = os.environ.get("GRAD_AGENT_HOME")
    if env:
        return Path(env).expanduser().resolve()
    default = Path.home() / ".grad-agent"
    if default.exists():
        return default
    # Legacy fallback: the folder containing the package
    return PACKAGE_ROOT.parent


def ensure_home() -> Path:
    h = home()
    h.mkdir(parents=True, exist_ok=True)
    (h / "data").mkdir(exist_ok=True)
    (h / "drafts").mkdir(exist_ok=True)
    return h


def profile_path() -> Path:  return home() / "profile.yaml"
def programs_path() -> Path: return home() / "programs.yaml"
def env_path() -> Path:      return home() / ".env"

def data_dir() -> Path:      ensure_home(); return home() / "data"
def drafts_dir() -> Path:    ensure_home(); return home() / "drafts"


@dataclass
class Profile:
    name: str = ""
    identity_line: str = ""
    portfolio: str = ""
    cv_path: str = ""
    transcript_path: str = ""
    degree_status: str = "bachelors"     # bachelors | masters
    target_term: str = "Fall 2027"
    target_degree: str = "PhD"           # PhD | MSc
    research_areas: list[str] = field(default_factory=list)
    projects_dir: str = ""
    seed_projects: list[dict] = field(default_factory=list)
    blog: dict = field(default_factory=dict)     # optional plugin config
    review_email: str = ""                       # where drafts are sent

    @property
    def has_masters(self) -> bool:
        return (self.degree_status or "").lower() == "masters"


@lru_cache(maxsize=1)
def load_profile() -> Profile:
    p = profile_path()
    if not p.exists() or yaml is None:
        return Profile()
    data = yaml.safe_load(p.read_text()) or {}
    return Profile(
        name=data.get("name", ""),
        identity_line=data.get("identity_line", ""),
        portfolio=data.get("portfolio", ""),
        cv_path=str(Path(data.get("cv_path", "")).expanduser()) if data.get("cv_path") else "",
        transcript_path=str(Path(data.get("transcript_path", "")).expanduser()) if data.get("transcript_path") else "",
        degree_status=data.get("degree_status", "bachelors"),
        target_term=data.get("target_term", "Fall 2027"),
        target_degree=data.get("target_degree", "PhD"),
        research_areas=data.get("research_areas", []) or [],
        projects_dir=str(Path(data.get("projects_dir", "")).expanduser()) if data.get("projects_dir") else "",
        seed_projects=data.get("seed_projects", []) or [],
        blog=data.get("blog", {}) or {},
        review_email=data.get("review_email", ""),
    )


def load_env_file() -> None:
    """Load .env from GRAD_AGENT_HOME. Silent if missing."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    p = env_path()
    if p.exists():
        load_dotenv(p, override=False)
    # legacy: also try package-local .env
    legacy = PACKAGE_ROOT.parent / ".env"
    if legacy.exists():
        load_dotenv(legacy, override=False)
