"""Program-driven targeting: instead of letting arXiv drive discovery, pick a
program (usually one with an approaching deadline), take its affiliated
faculty, verify each, and draft. Deadline-driven beats paper-driven when
application season arrives.

Faculty come from two sources per program:
  1. `affiliated_faculty` list in programs.yaml (curated).
  2. Optional `faculty_url`: a department people page. The page text is
     fetched and Claude Haiku extracts professor names from it.
"""
from __future__ import annotations
import os
import re
import time

from . import config as _cfg
from . import outreach_log
from . import projects
from . import programs
from . import hook
from . import freshness
from .drafters import cold_email
from .outputs import mailer
from .sources import semantic_scholar as s2, recruiting

try:
    import anthropic
except Exception:
    anthropic = None


def _faculty_from_url(url: str, limit: int = 30) -> list[str]:
    """Fetch a faculty page and let Haiku extract professor names."""
    if not url:
        return []
    try:
        import httpx
        from bs4 import BeautifulSoup
        r = httpx.get(url, timeout=30, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return []
        text = BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)[:12000]
    except Exception:
        return []
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return []
    try:
        client = anthropic.Anthropic()
        m = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=800,
            system=(
                "Extract the names of faculty members (professors, associate "
                "professors, assistant professors) from this department page "
                "text. Return one full name per line, nothing else. Skip "
                "students, postdocs, and staff."
            ),
            messages=[{"role": "user", "content": text}],
        )
        names = [ln.strip() for ln in m.content[0].text.splitlines() if ln.strip()]
        return [n for n in names if len(n.split()) >= 2][:limit]
    except Exception:
        return []


def run_program_batch(program_id: str, n: int = 3, dry_run: bool = False) -> dict:
    """Draft cold emails for up to n verified, uncontacted faculty of a program."""
    prog = next((p for p in programs.all_programs() if p.get("id") == program_id), None)
    if not prog:
        return {"error": f"unknown program id: {program_id}. "
                         f"See list_programs() for valid ids."}
    gate = programs.eligibility(prog)
    if not gate["eligible"]:
        return {"error": f"program blocked: {gate['reason']}"}

    names = list(prog.get("affiliated_faculty") or [])
    names += _faculty_from_url(prog.get("faculty_url", ""))
    # de-dup while keeping curated names first
    seen: set[str] = set()
    ordered = []
    for nm in names:
        k = nm.strip().lower()
        if k and k not in seen:
            seen.add(k)
            ordered.append(nm.strip())

    if not ordered:
        return {"error": "program has no affiliated_faculty and no usable faculty_url"}

    try:
        boost = outreach_log.project_response_boost()
    except Exception:
        boost = {}

    drafts, skipped = [], []
    for name in ordered:
        if len(drafts) >= n:
            break
        # Curated faculty are already human-verified in programs.yaml, but the
        # NAME still has to resolve to the right S2 entity. Anchor on the
        # program's university; ambiguous identities are skipped, not guessed.
        v = s2.resolve_for_program(name, prog.get("university", ""))
        if not v.get("author_id"):
            reason = v.get("reason", "no S2 record")
            skipped.append({"prof": name, "why": reason})
            outreach_log.add_skip(name, "identity", reason,
                                  source=f"program:{program_id}",
                                  resolution=v.get("resolution", ""))
            continue
        verification_note = "" if v.get("ok") else f"soft-pass: {v.get('reason')}"
        if v.get("resolution"):
            verification_note = (verification_note + "  " if verification_note else "") \
                                + f"identity: {v['resolution']}"
        if outreach_log.already_contacted(name, author_id=v.get("author_id")):
            skipped.append({"prof": name, "why": "already contacted"})
            outreach_log.add_skip(name, "dedup", "already contacted",
                                  source=f"program:{program_id}",
                                  resolution=v.get("resolution", ""))
            continue
        recents = s2.recent_papers(v["author_id"], limit=5)
        if not recents:
            skipped.append({"prof": name, "why": "no recent papers with abstracts"})
            outreach_log.add_skip(name, "no-papers",
                                  "no recent papers with abstracts",
                                  source=f"program:{program_id}",
                                  resolution=v.get("resolution", ""))
            continue
        surface = " ".join(p.get("title", "") + " " + (p.get("abstract") or "")
                           for p in recents[:2])
        match = projects.best_project(recents[0].get("title", ""), surface,
                                      outcome_boost=boost)
        h = hook.build(papers=recents[:3], project_name=match["name"],
                       project_pitch=match["pitch"],
                       project_tags=match.get("tags", []))
        fit = hook.fit_score(recents[:3], match["name"], match["pitch"])
        rec = recruiting.signal(v.get("homepage") or "")
        aff_fresh = freshness.affiliation_check(
            (v.get("affiliations") or [""])[0], rec.get("page_text", ""))
        act_fresh = freshness.activity_check(recents)
        last = name.split()[-1]
        d = cold_email.build(
            prof_name=name, prof_lastname=last,
            university=prog.get("university", ""),
            their_paper_title=recents[0].get("title", ""),
            substantive_hook=h["hook"],
            your_project_name=match["name"],
            your_project_link=match["link"],
            degree=prog.get("degree"),
        )
        drafts.append({"prof_name": name, "verify": v, "recruiting": rec,
                       "match": match, "hook": h, "fit": fit, "email": d,
                       "paper": recents[0],
                       "verification_note": verification_note,
                       "aff_fresh": aff_fresh, "act_fresh": act_fresh})

    for d in drafts:
        v = d["verify"]; rec = d["recruiting"]
        outreach_log.add(
            prof_name=d["prof_name"],
            prof_lastname=d["prof_name"].split()[-1],
            prof_email=rec.get("email") or "",
            university=prog.get("university", ""),
            program_target=program_id,
            area=prog.get("degree", ""),
            paper_title=d["paper"].get("title", ""),
            paper_url=d["paper"].get("url") or "",
            project_matched=d["match"]["name"],
            match_score=d["match"]["score"],
            email_subject=d["email"]["subject"],
            review_mail_sent_at=time.strftime("%Y-%m-%d %H:%M"),
            s2_hindex=v.get("h_index"), s2_papers=v.get("paper_count"),
            affiliation=(v.get("affiliations") or [""])[0],
            homepage=v.get("homepage") or "",
            recruiting_signal="yes" if rec.get("recruiting") else "no",
            hook_attempts=d["hook"].get("attempts", 1),
            hook_verdict=d["hook"].get("verification", {}).get("verdict", ""),
            s2_author_id=v.get("author_id") or "",
            fit_score=d["fit"].get("score", ""),
            fit_reason=d["fit"].get("reason", ""),
        )

    deadline = prog.get("deadline", "unknown")
    lines = [
        f"Program-targeted batch: {program_id} ({prog.get('university')})",
        f"Degree: {prog.get('degree')}  Deadline: {deadline}",
        f"Drafted: {len(drafts)}  Skipped: {len(skipped)}",
        "",
    ]
    for s in skipped[:10]:
        lines.append(f"  skipped {s['prof']}: {s['why']}")
    lines.append("")
    drafts.sort(key=lambda d: -(d["fit"].get("score") or 0))
    for i, d in enumerate(drafts, 1):
        e = d["email"]
        lines += [
            "=" * 72,
            f"[{i}] {d['prof_name']}  FIT: {d['fit'].get('score','?')}/10  ({d['fit'].get('reason','')})",
            *([f"Note: {d['verification_note']}"] if d.get("verification_note") else []),
            f"Freshness: {d.get('aff_fresh', {}).get('note', '')}  |  {d.get('act_fresh', {}).get('note', '')}",
            f"Email guess: {d['recruiting'].get('email') or '(verify manually)'}",
            f"Matched project: {d['match']['name']}",
            "",
            f"Subject: {e['subject']}",
            "",
            e["body"],
            "",
        ]
    body = "\n".join(lines)

    if dry_run:
        return {"program": program_id, "drafted": len(drafts),
                "skipped": len(skipped), "preview": body[:3000]}
    if not drafts:
        return {"program": program_id, "drafted": 0, "skipped": len(skipped),
                "skip_reasons": skipped[:10]}

    prof_cfg = _cfg.load_profile()
    attachments = [p for p in (prof_cfg.cv_path, prof_cfg.transcript_path)
                   if p and os.path.exists(p)]
    res = mailer.send_to_me(
        subject=f"Program batch {program_id}, {len(drafts)} drafts, deadline {deadline}",
        body=body, attachments=attachments)
    return {"program": program_id, "drafted": len(drafts),
            "skipped": len(skipped), "mail": res}
