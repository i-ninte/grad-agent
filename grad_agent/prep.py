"""Interview prep pack. When a professor replies positively, generate a
one-pager: their recent papers summarised, likely questions, the user's
talking points mapped to the prof's work, and three questions to ask.
Saved to drafts/prep/ and optionally emailed to the review inbox.
"""
from __future__ import annotations
import os
import re

from . import config as _cfg
from . import projects
from .sources import semantic_scholar as s2
from .outputs import mailer

try:
    import anthropic
except Exception:
    anthropic = None

SYSTEM = (
    "You prepare a graduate applicant for a call with a professor. Given the "
    "professor's recent papers and the applicant's projects, write a one page "
    "markdown brief with exactly these sections:\n"
    "## Their recent work\n(3 to 5 bullet summaries, one per paper, concrete)\n"
    "## Questions they will likely ask you\n(5 bullets, grounded in the gap "
    "between the applicant's background and the professor's research)\n"
    "## Your talking points\n(4 bullets mapping the applicant's specific "
    "projects to threads in the professor's work)\n"
    "## Three questions to ask them\n(3 bullets, questions that show the "
    "applicant read the work; never questions answerable by reading the abstract)\n"
    "Plain prose, no dashes in sentences, no filler words (passionate, delve, "
    "leverage, cutting edge). Direct, technically grounded."
)


def build(prof_name: str, send_to_inbox: bool = True) -> dict:
    v = s2.verify_by_name(prof_name)
    if not v.get("author_id"):
        return {"error": f"could not resolve {prof_name} on Semantic Scholar"}
    papers = s2.recent_papers(v["author_id"], limit=5)
    if not papers:
        return {"error": f"no recent papers with abstracts for {prof_name}"}
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return {"error": "ANTHROPIC_API_KEY required for prep generation"}

    profile = _cfg.load_profile()
    top_projects = projects.rank_projects(
        papers[0].get("title", ""),
        " ".join(p.get("abstract", "") for p in papers[:3]),
        top_k=4,
    )
    paper_block = "\n\n".join(
        f"[{i+1}] {p.get('title','')} ({p.get('year','')}, {p.get('venue','') or 'preprint'})\n"
        f"{(p.get('abstract') or '')[:1200]}"
        for i, p in enumerate(papers)
    )
    project_block = "\n".join(
        f"- {p['name']}: {p['pitch']}" for p in top_projects
    )

    client = anthropic.Anthropic()
    m = client.messages.create(
        model="claude-haiku-4-5-20251001", max_tokens=1800, system=SYSTEM,
        messages=[{"role": "user", "content": (
            f"PROFESSOR: {v.get('name')} ({(v.get('affiliations') or ['unknown'])[0]})\n\n"
            f"RECENT PAPERS:\n{paper_block}\n\n"
            f"APPLICANT: {profile.name}, {profile.identity_line}\n"
            f"APPLICANT'S RELEVANT PROJECTS:\n{project_block}\n\n"
            f"Write the brief now."
        )}],
    )
    brief = m.content[0].text.strip()
    brief = brief.replace("—", ", ").replace("–", ", ")

    slug = re.sub(r"[^a-z0-9]+", "_", prof_name.lower()).strip("_")
    out_dir = _cfg.drafts_dir() / "prep"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.md"
    header = (
        f"# Prep: {v.get('name')}\n\n"
        f"Affiliation: {(v.get('affiliations') or ['unknown'])[0]}  \n"
        f"h-index: {v.get('h_index')}  Papers: {v.get('paper_count')}  \n"
        f"Homepage: {v.get('homepage') or 'n/a'}\n\n---\n\n"
    )
    path.write_text(header + brief)

    result = {"path": str(path), "prof": v.get("name"),
              "papers_used": len(papers)}
    if send_to_inbox:
        try:
            result["mail"] = mailer.send_to_me(
                subject=f"Interview prep: {v.get('name')}",
                body=header + brief, attachments=[str(path)])
        except Exception as e:
            result["mail_error"] = str(e)
    return result
