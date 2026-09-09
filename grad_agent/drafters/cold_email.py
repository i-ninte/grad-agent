"""Cold email drafter for prospective PhD/MSc outreach.

Rules distilled from Raiaan (ColdEmailPhDMSc), academiatoindustry, sowasser,
Zach Rewolinski. Encoded here so every draft passes the same bar.

Structure (3 paragraphs, <=300 words total, readable in <60s):
  1. Intro <=50 words. Who you are, current role, most recent degree.
     No GPA/CGPA numerically unless the sender flags themselves as top decile
     (allow_gpa=True), in which case a First Class / CWA line is permitted.
  2. Fit <=120 words. Reference a specific recent (<=3 yrs) paper the prof
     first- or last-authored, OR a current grant. Make a technical observation
     that goes past the abstract, then pose ONE substantive research question.
     Never restate the abstract. Never say "I read your paper" as filler; talk
     about the work itself.
  3. Contribution <=100 words. Name 1-2 of YOUR projects that map to the lab's
     stated needs, and say what you would try to extend or build. Frame as
     "here is what I can contribute", not "here is my resume".

Then CTA: ask for a ~30 minute conversation. Never ask for a position, funding,
or "any openings".

Hard bans (regex-checked): hope this/you well, esteemed, express my interest,
any (available) positions, delve, leverage, tapestry, I am writing to,
I would love, kindly, honored, and every en/em dash.
"""
from __future__ import annotations
import re
from datetime import datetime


BANNED = [
    r"hope (this|you).{0,20}well",
    r"esteemed",
    r"express my interest",
    r"any (available )?positions?",
    r"do you have openings",
    r"i am writing to",
    r"i would love",
    r"kindly",
    r"honored",
    r"delve",
    r"leverage",
    r"tapestry",
    r"holistic",
    r"cutting.?edge",
    r"ever.?evolving",
    r"passionate",
    r"reaching out",
    r"i read your (recent )?paper",
    r"\bCGPA\b",
    r"\bGPA\b",
]

_DASH_REWRITES = [("—", ", "), ("–", ", "), (" - ", ", ")]


def _strip_dashes(text: str) -> str:
    out = text
    for a, b in _DASH_REWRITES:
        out = out.replace(a, b)
    lines = out.split("\n")
    lines = [re.sub(r",\s*,", ",", re.sub(r"[ \t]+", " ", ln)).strip() for ln in lines]
    return "\n".join(lines)


def _scrub(text: str, allow: set[str] | None = None) -> list[str]:
    allow = allow or set()
    hits = []
    for pat in BANNED:
        if pat in allow:
            continue
        if re.search(pat, text, re.I):
            hits.append(pat)
    return hits


def _wc(s: str) -> int:
    return len(s.split())


def build(
    *,
    prof_lastname: str,
    prof_title: str = "Prof.",
    sender_name: str,
    sender_role_line: str,
    target_term: str,
    degree: str,
    research_area: str,
    # Fit paragraph inputs
    paper_title: str,
    paper_year: int,
    paper_technical_point: str,
    research_question: str,
    prof_is_first_or_last_author: bool = True,
    # Contribution paragraph inputs
    own_projects: list[dict],  # [{name, one_liner, link_or_venue}]
    contribution_line: str,     # "I would like to extend X toward Y"
    portfolio_url: str,
    allow_gpa: bool = False,
    credentials_line: str | None = None,  # e.g. "First Class, CWA 76.74"
) -> dict:
    warnings: list[str] = []
    current_year = datetime.now().year
    if paper_year < current_year - 3:
        warnings.append(f"paper is {current_year - paper_year} years old (rule: <=3)")
    if not prof_is_first_or_last_author:
        warnings.append("cited paper is not first/last authored by prof")

    first_name = sender_name.split()[0]

    intro = f"I am {sender_name}, {sender_role_line}."
    if credentials_line and allow_gpa:
        intro += f" {credentials_line}."

    fit = (
        f"Your {paper_year} work, \"{paper_title}\", {paper_technical_point} "
        f"This raises a question I would like to work on: {research_question}"
    )

    proj_lines = []
    for p in own_projects[:2]:
        line = f"{p['name']} ({p['one_liner']})"
        if p.get("link_or_venue"):
            line += f", {p['link_or_venue']}"
        proj_lines.append(line)
    projects_blob = "; ".join(proj_lines)
    contribution = (
        f"On my side, {projects_blob}. {contribution_line}"
    )

    cta = (
        f"I plan to apply for a fully funded {degree} for {target_term} and "
        f"would list you as prospective advisor. Would a thirty minute call "
        f"work once you have looked at my CV? More at {portfolio_url}."
    )

    body = (
        f"Dear {prof_title} {prof_lastname},\n\n"
        f"{intro}\n\n"
        f"{fit}\n\n"
        f"{contribution}\n\n"
        f"{cta}\n\n"
        f"Thanks,\n{first_name}"
    )
    body = _strip_dashes(body)

    allow = {r"\bGPA\b", r"\bCGPA\b"} if allow_gpa else set()
    banned_hits = _scrub(body, allow=allow)

    counts = {
        "intro": _wc(intro),
        "fit": _wc(fit),
        "contribution": _wc(contribution),
        "cta": _wc(cta),
        "total": _wc(body),
    }
    if counts["intro"] > 50:
        warnings.append(f"intro {counts['intro']}w > 50")
    if counts["fit"] > 120:
        warnings.append(f"fit {counts['fit']}w > 120")
    if counts["contribution"] > 100:
        warnings.append(f"contribution {counts['contribution']}w > 100")
    if counts["total"] > 300:
        warnings.append(f"total {counts['total']}w > 300")

    subject = _strip_dashes(
        f"Prospective {degree} Applicant for {target_term} Interested in {research_area}"
    )

    return {
        "subject": subject,
        "body": body,
        "counts": counts,
        "banned_hits": banned_hits,
        "warnings": warnings,
        "has_dashes": ("—" in body) or ("–" in body) or (" - " in body),
        "ok": not banned_hits and not warnings,
    }


def build_from_hook(
    *,
    prof_name: str,
    prof_lastname: str,
    university: str,
    their_paper_title: str,
    substantive_hook: str,
    your_project_name: str,
    your_project_link: str,
    target_term: str | None = None,
    degree: str | None = None,
    **_ignored,
) -> dict:
    """Legacy adapter for the auto-batch pipeline (daily_run, program_targeting,
    server.draft_cold_email). Consumes hook.build() output. New human-authored
    outreach should call build() directly with the full structured inputs."""
    try:
        from .. import config as _cfg
        prof = _cfg.load_profile()
        sender_name = prof.name or "the sender"
        identity = prof.identity_line or "a graduate applicant"
        target_term = target_term or prof.target_term or "Fall 2027"
        degree = degree or prof.target_degree or "PhD"
        portfolio = getattr(prof, "portfolio", "") or your_project_link
    except Exception:
        sender_name, identity = "the sender", "a graduate applicant"
        target_term = target_term or "Fall 2027"
        degree = degree or "PhD"
        portfolio = your_project_link

    first = sender_name.split()[0]
    body = (
        f"Dear Prof. {prof_lastname},\n\n"
        f"I am {sender_name}, {identity}.\n\n"
        f"Your work, \"{their_paper_title}\". {substantive_hook}\n\n"
        f"On my side, {your_project_name} at {your_project_link} is the closest "
        f"line of work I could bring in.\n\n"
        f"I plan to apply for a fully funded {degree} for {target_term} and "
        f"would list you as prospective advisor. Would a thirty minute call "
        f"work once you have looked at my CV? More at {portfolio}.\n\n"
        f"Thanks,\n{first}"
    )
    body = _strip_dashes(body)
    banned_hits = _scrub(body)
    subject = _strip_dashes(
        f"Prospective {degree} Applicant for {target_term}, {your_project_name}"
    )
    wc = _wc(body)
    return {
        "subject": subject,
        "body": body,
        "word_count": wc,
        "banned_hits": banned_hits,
        "has_dashes": ("—" in body) or ("–" in body) or (" - " in body),
        "ok": wc <= 300 and not banned_hits,
    }
