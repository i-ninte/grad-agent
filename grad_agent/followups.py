"""Follow-up scheduler. Profs who were emailed but have not replied after N
days get a short, dashless nudge drafted into the review inbox. Nothing is
sent to a professor; the user sends and then the row is marked so a prof is
never nudged twice.
"""
from __future__ import annotations

from . import config as _cfg
from . import outreach_log


def _nudge_text(row: dict) -> str:
    prof_last = str(row.get("prof_lastname") or
                    str(row.get("prof_name") or "").split()[-1])
    paper = str(row.get("paper_title") or "your recent work")
    prof = _cfg.load_profile()
    first = (prof.name or "the applicant").split()[0]
    term = prof.target_term or "the coming intake"
    return (
        f"Dear Prof. {prof_last},\n\n"
        f"Following up briefly on my note from {row.get('days_since_sent', 'a couple of weeks')} days ago "
        f"about \"{paper}\" and a funded position for {term}. I know inboxes "
        f"pile up, so one line is enough: is it worth my applying to work "
        f"with you this cycle?\n\n"
        f"CV and portfolio, {prof.portfolio}\n\n"
        f"Thanks,\n{first}"
    )


def build_due(days: int = 10) -> list[dict]:
    """Return due follow-ups, each with a drafted nudge attached."""
    due = outreach_log.followups_due(days=days)
    out = []
    for row in due:
        subject = str(row.get("email_subject") or "").strip()
        out.append({
            "prof_name": row.get("prof_name"),
            "prof_email": row.get("prof_email") or "(verify manually)",
            "days_since_sent": row.get("days_since_sent"),
            "subject": f"Re: {subject}" if subject else "Following up",
            "body": _nudge_text(row),
        })
    return out


def review_email_section(days: int = 10) -> list[str]:
    """Lines for the daily review email. Empty list when nothing is due."""
    due = build_due(days=days)
    if not due:
        return []
    lines = [f"FOLLOW-UPS DUE ({len(due)}): sent {days}+ days ago, no reply, no nudge yet."]
    for d in due:
        lines += [
            "-" * 60,
            f"To: {d['prof_name']} <{d['prof_email']}>  ({d['days_since_sent']}d silent)",
            f"Subject: {d['subject']}",
            "",
            d["body"],
            "",
            f"(after sending, run: outreach_mark_followup(\"{d['prof_name']}\"))",
        ]
    lines.append("")
    return lines
