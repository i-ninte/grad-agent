"""Cold email drafter. Direct, no AI-lingo, NO dashes anywhere.

Structure (5 short paragraphs, <=180 words total):
1. One line: who + where + what you do.
2. One line about THEIR specific paper.
3. One line linking YOUR concrete project to their work.
4. The ask (funded MSc/PhD, term).
5. Sign off with portfolio link.
"""
from __future__ import annotations
import re

BANNED = [
    "passionate", "deeply", "reaching out", "hope this finds",
    "honored", "delve", "tapestry", "leverage", "holistic",
    "i would love", "kindly", "i am writing to", "furthermore",
    "moreover", "in today's world", "ever-evolving", "cutting-edge",
]

# Every en/em dash and any lingering hyphen used as a clause separator gets rewritten.
_DASH_REWRITES = [
    ("—", ", "),
    ("–", ", "),
    (" - ", ", "),
]


def _strip_dashes(text: str) -> str:
    out = text
    for a, b in _DASH_REWRITES:
        out = out.replace(a, b)
    # collapse accidental ", , " runs, but preserve newlines
    lines = out.split("\n")
    lines = [re.sub(r",\s*,", ",", re.sub(r"[ \t]+", " ", ln)).strip() for ln in lines]
    return "\n".join(lines)


def _scrub(text: str) -> tuple[str, list[str]]:
    hits = [w for w in BANNED if re.search(rf"\b{re.escape(w)}\b", text, re.I)]
    return text, hits


def build(
    prof_name: str,
    prof_lastname: str,
    university: str,
    their_paper_title: str,
    substantive_hook: str,
    your_project_name: str,
    your_project_link: str,
    target_term: str | None = None,
    degree: str | None = None,
    identity_line: str | None = None,
    sender_name: str | None = None,
    their_paper_takeaway: str | None = None,
    your_one_line_connection: str | None = None,
) -> dict:
    # Read defaults from the user's profile.yaml so this drafter is portable.
    try:
        from .. import config as _cfg
        prof = _cfg.load_profile()
        sender_name = sender_name or prof.name or "the sender"
        identity_line = identity_line or prof.identity_line or "a graduate applicant"
        target_term = target_term or prof.target_term
        degree = degree or prof.target_degree
    except Exception:
        sender_name = sender_name or "the sender"
        identity_line = identity_line or "a graduate applicant"
        target_term = target_term or "Fall 2027"
        degree = degree or "PhD"

    first_name = sender_name.split()[0] if sender_name else "Applicant"
    raw = (
        f"Dear Prof. {prof_lastname},\n\n"
        f"I am {sender_name}, {identity_line}, working on applied ML across NLP, "
        f"computer vision, and low resource systems.\n\n"
        f"I read your recent paper, \"{their_paper_title}\". {substantive_hook}\n\n"
        f"More on the project I mention above, and the rest of my work, at "
        f"{your_project_link}.\n\n"
        f"I am applying for a fully funded {degree} for {target_term}. Are you "
        f"taking students, and would a fifteen minute call make sense?\n\n"
        f"Thanks,\n{first_name}"
    )
    body = _strip_dashes(raw)
    body, banned_hits = _scrub(body)
    word_count = len(body.split())
    subject = f"Prospective {degree} student, {target_term}, {your_project_name}"
    subject = _strip_dashes(subject)
    return {
        "subject": subject,
        "body": body,
        "word_count": word_count,
        "banned_hits": banned_hits,
        "has_dashes": ("—" in body) or ("–" in body) or (" - " in body),
        "ok": word_count <= 200 and not banned_hits,
    }
