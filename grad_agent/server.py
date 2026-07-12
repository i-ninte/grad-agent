#!/Users/ninte/Desktop/NINTE/GRAD/grad-agent/.venv/bin/python
"""grad-agent MCP server.

Run:  python server.py
Or register in Claude Desktop / Cursor via mcpServers config.

Every tool returns JSON-serializable dicts. Drafts are always written to disk
first; nothing sends to a prof automatically.
"""
from __future__ import annotations
import os, json
from pathlib import Path

from . import config as _cfg
_cfg.load_env_file()

from fastmcp import FastMCP

from . import profile_pdf as prof
from . import tracker
from . import outreach_log
from .sources import arxiv, openreview, websearch
from .drafters import cold_email, sop_latex
from .outputs import mailer
from . import daily_run
from . import catalog_sync
from . import projects as _projects_mod
from . import programs as _programs_mod
from . import lor as _lor_mod

# Optional blog plugin: only load if the user opted in via profile.yaml.
_blog_enabled = bool(_cfg.load_profile().blog.get("enabled"))
if _blog_enabled:
    try:
        from .drafters import article  # noqa: F401
        from .outputs import portfolio_api  # noqa: F401
    except Exception:
        _blog_enabled = False

mcp = FastMCP("grad-agent")
DRAFTS = _cfg.drafts_dir()
DRAFTS.mkdir(exist_ok=True)


# ─── profile ───────────────────────────────────────────────────
@mcp.tool()
def load_profile() -> dict:
    """Load and cache CV + transcript. Call once per session."""
    p = prof.load()
    return {"name": p["name"], "cv_chars": len(p["cv_text"]),
            "transcript_chars": len(p["transcript_text"]),
            "summary": prof.summary()}


# ─── discovery ────────────────────────────────────────────────
@mcp.tool()
def discover_profs(area: str, max_results: int = 20) -> dict:
    """Fan out arXiv + OpenReview for recent papers in `area`
    (nlp|llm|ml|cv|ai4health|africa or raw query). Returns candidates
    with authors as prof leads."""
    ax = arxiv.search(area, max_results=max_results)
    orv = openreview.recent("iclr", limit=10)
    return {"arxiv": ax, "openreview": orv}


@mcp.tool()
def find_prof_page(name: str, university: str = "") -> list[dict]:
    """Web search for a professor's lab page / email."""
    return websearch.find_prof_page(name, university)


# ─── pipeline ──────────────────────────────────────────────────
@mcp.tool()
def add_target(prof_name: str, prof_email: str = "", university: str = "",
               program: str = "", area: str = "", deadline: str = "",
               paper_url: str = "", notes: str = "") -> dict:
    tid = tracker.add_target(
        prof_name=prof_name, prof_email=prof_email, university=university,
        program=program, area=area, deadline=deadline, paper_url=paper_url,
        notes=notes,
    )
    return {"target_id": tid}


@mcp.tool()
def list_pipeline(status: str = "") -> list[dict]:
    """status: '' (all) | new | drafted | sent | replied | rejected | silent"""
    return tracker.list_pipeline(status or None)


@mcp.tool()
def mark_status(target_id: int, status: str) -> dict:
    tracker.set_status(target_id, status)
    return {"ok": True, "target_id": target_id, "status": status}


# ─── drafting ──────────────────────────────────────────────────
@mcp.tool()
def draft_cold_email(target_id: int, prof_name: str, prof_lastname: str,
                     university: str, their_paper_title: str,
                     their_paper_takeaway: str, your_project_name: str,
                     your_project_link: str, your_one_line_connection: str,
                     target_term: str = "Fall 2027",
                     degree: str = "PhD") -> dict:
    """Draft a cold email. Saves to drafts/, returns preview + banned_hits."""
    d = cold_email.build(
        prof_name=prof_name, prof_lastname=prof_lastname, university=university,
        their_paper_title=their_paper_title, their_paper_takeaway=their_paper_takeaway,
        your_project_name=your_project_name, your_project_link=your_project_link,
        your_one_line_connection=your_one_line_connection,
        target_term=target_term, degree=degree,
    )
    slug = f"{university}_{prof_lastname}".replace(" ", "_")
    outdir = DRAFTS / slug; outdir.mkdir(parents=True, exist_ok=True)
    fp = outdir / "email.txt"
    fp.write_text(f"Subject: {d['subject']}\n\n{d['body']}")
    tracker.add_draft(target_id, "email", str(fp), d["subject"])
    return {"path": str(fp), **d}


@mcp.tool()
def draft_sop(target_id: int, university: str, university_short: str,
              degree_line: str, header_left: str,
              opening: str, vision_paragraph: str,
              t1_head: str, t1_body: str,
              t2_head: str, t2_body: str,
              t3_head: str, t3_body: str,
              why_university: str, teaching: str, long_term: str) -> dict:
    """Draft a Columbia-style SOP and compile to PDF. Returns {tex, pdf}."""
    slug = (university_short + "_" + degree_line).replace(" ", "_").replace(",", "")
    outdir = DRAFTS / slug
    out = sop_latex.build(
        university=university, university_short=university_short,
        degree_line=degree_line, header_left=header_left,
        opening=opening, vision_paragraph=vision_paragraph,
        t1_head=t1_head, t1_body=t1_body,
        t2_head=t2_head, t2_body=t2_body,
        t3_head=t3_head, t3_body=t3_body,
        why_university=why_university, teaching=teaching, long_term=long_term,
        out_dir=str(outdir),
    )
    tracker.add_draft(target_id, "sop", out["pdf"] or out["tex"],
                      f"SOP {university_short} {degree_line}")
    return out


@mcp.tool()
def draft_article(project_name: str, angle: str = "engineering deep-dive") -> dict:
    """Draft a blog post. Requires blog.enabled: true in profile.yaml."""
    if not _blog_enabled:
        return {"error": "blog plugin disabled; set blog.enabled: true in profile.yaml"}
    from .drafters import article as _article
    p = prof.load()
    d = _article.draft(project_name, p["ninte_root"], angle=angle)
    if "error" in d: return d
    fp = DRAFTS / f"article_{project_name}.md"
    fp.write_text(d["content"])
    return {"path": str(fp), **d}


# ─── outputs ───────────────────────────────────────────────────
@mcp.tool()
def send_draft_to_me(path: str, note: str = "") -> dict:
    """Emails the draft file to your inbox (NOTIFY_TO)."""
    body = Path(path).read_text()
    subj = f"Draft: {Path(path).name}" + (f" — {note}" if note else "")
    return mailer.send_to_me(subject=subj, body=body, attachments=[path])


def _md_meta(path: str) -> tuple[str, str, str]:
    content = Path(path).read_text()
    lines = content.splitlines()
    title = lines[0].lstrip("# ").strip() if lines else Path(path).stem
    excerpt = next(
        (l.strip().lstrip("*_ ").rstrip("*_ ") for l in lines[1:]
         if l.strip() and not l.startswith("#") and not l.startswith("---")),
        "",
    )[:200]
    return title, excerpt, content


def _blog_guard():
    if not _blog_enabled:
        return {"error": "blog plugin disabled; set blog.enabled: true in profile.yaml"}
    return None


@mcp.tool()
def publish_article(path: str, publish: bool = False) -> dict:
    if (g := _blog_guard()): return g
    from .outputs import portfolio_api as _pa
    title, excerpt, content = _md_meta(path)
    return _pa.create_post(title=title, content=content, excerpt=excerpt, publish=publish)


@mcp.tool()
def update_article(post_id: str, path: str, publish: bool | None = None) -> dict:
    if (g := _blog_guard()): return g
    from .outputs import portfolio_api as _pa
    title, excerpt, content = _md_meta(path)
    return _pa.update_post(post_id=post_id, title=title, content=content,
                           excerpt=excerpt, publish=publish)


@mcp.tool()
def delete_post(post_id: str) -> dict:
    if (g := _blog_guard()): return g
    from .outputs import portfolio_api as _pa
    return _pa.delete_post(post_id)


@mcp.tool()
def list_posts() -> list[dict]:
    if (g := _blog_guard()): return [g]
    from .outputs import portfolio_api as _pa
    return _pa.list_posts()


# ─── autonomous batch ─────────────────────────────────────────
@mcp.tool()
def run_daily_batch(n: int = 3, area: str = "") -> dict:
    """Run the daily outreach: pick n unseen profs in `area` (or today's rotation),
    match to your strongest project, draft dashless cold emails, log to xlsx,
    and email the batch to your review inbox."""
    return daily_run.run_batch(n=n, area=area or None)


@mcp.tool()
def outreach_log_view(limit: int = 25) -> list[dict]:
    """Show the last N rows of the outreach xlsx."""
    return outreach_log.list_all(limit=limit)


@mcp.tool()
def sync_catalog(source: str = "all") -> dict:
    """Extend the project catalog. source in {all, github, huggingface, local}."""
    if source == "github":     return {"added": catalog_sync.sync_github()}
    if source == "huggingface": return {"added": catalog_sync.sync_hf()}
    if source == "local":      return {"added": catalog_sync.sync_local()}
    return catalog_sync.sync_all()


@mcp.tool()
def list_projects_in_catalog() -> list[dict]:
    """Return the current unified catalog (seed + synced)."""
    return _projects_mod._all_projects()


@mcp.tool()
def outreach_mark_sent(prof_name: str, university: str = "") -> dict:
    ok = outreach_log.mark_sent(prof_name, university)
    return {"updated": ok, "prof_name": prof_name}


@mcp.tool()
def outreach_mark_response(prof_name: str, outcome: str, notes: str = "") -> dict:
    """Tag a prof's reply. outcome: positive | negative | no_response | interview.
    These tags feed the matcher: projects that earn replies rank up in future runs."""
    ok = outreach_log.mark_response(prof_name, outcome, notes)
    return {"updated": ok, "prof_name": prof_name, "outcome": outcome}


@mcp.tool()
def outcome_report() -> dict:
    """Response-rate report from your tagged outcomes: totals, by area, by project."""
    return outreach_log.outcome_stats()


@mcp.tool()
def followups_due(days: int = 10) -> list[dict]:
    """Profs emailed `days`+ ago with no reply and no nudge yet, each with a
    drafted follow-up ready to review and send."""
    from . import followups as _fu
    return _fu.build_due(days=days)


@mcp.tool()
def outreach_mark_followup(prof_name: str) -> dict:
    """Record that you sent the follow-up nudge, so the prof is never nudged twice."""
    ok = outreach_log.mark_followup_sent(prof_name)
    return {"updated": ok, "prof_name": prof_name}


@mcp.tool()
def ingest_replies() -> dict:
    """Read-only IMAP scan: detect professor replies and tag the outreach log.
    Needs IMAP creds in .env (defaults to Gmail + SMTP credentials)."""
    from .outputs import imap_ingest as _imap
    return _imap.ingest()


@mcp.tool()
def run_program_batch(program_id: str, n: int = 3) -> dict:
    """Deadline-driven batch: verify + draft for faculty of one program from
    programs.yaml instead of arXiv discovery. Use before application deadlines."""
    from . import program_targeting as _pt
    return _pt.run_program_batch(program_id=program_id, n=n)


@mcp.tool()
def interview_prep(prof_name: str, send_to_inbox: bool = True) -> dict:
    """Generate a one-page interview brief for a prof who replied: their recent
    papers summarised, likely questions, your talking points, questions to ask."""
    from . import prep as _prep
    return _prep.build(prof_name, send_to_inbox=send_to_inbox)


@mcp.tool()
def list_scholarships(region: str = "") -> list[dict]:
    """External scholarships from scholarships.yaml, optionally filtered by
    eligibility region (US, Canada, UK, EU, Asia, Africa, Australia)."""
    from . import scholarships as _sch
    return _sch.eligible(region)


@mcp.tool()
def upcoming_scholarship_deadlines(days: int = 60, region: str = "") -> list[dict]:
    from . import scholarships as _sch
    return _sch.upcoming_deadlines(days=days, user_region=region)


@mcp.tool()
def list_programs() -> list[dict]:
    return _programs_mod.all_programs()


@mcp.tool()
def upcoming_deadlines(days: int = 45) -> list[dict]:
    return _programs_mod.upcoming_deadlines(days)


@mcp.tool()
def lor_add(recommender: str, email: str = "", school: str = "",
            program_id: str = "", notes: str = "") -> dict:
    n = _lor_mod.add(recommender, email, school, program_id, notes)
    return {"row": n, "path": _lor_mod.path()}


@mcp.tool()
def lor_outstanding() -> list[dict]:
    return _lor_mod.outstanding()


@mcp.tool()
def lor_mark(recommender: str, school: str, field: str, value: str = "") -> dict:
    ok = _lor_mod.mark(recommender, school, field, value)
    return {"updated": ok}


if __name__ == "__main__":
    mcp.run()
