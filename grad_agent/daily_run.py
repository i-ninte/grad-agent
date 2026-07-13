"""Autonomous daily driver, v2.

Per candidate found on arXiv:
  1. Semantic Scholar verify: is this really a faculty PI? Skip if not.
  2. Fetch their recent papers (top 3) and homepage.
  3. Scrape homepage for recruiting signal + email.
  4. Match to Kwabena's strongest promoted project.
  5. Multi-paper hook with claim verification.
  6. Check if any seeded program lists them; note it.
  7. Draft dashless email, append to xlsx log, skip if already contacted.

Nothing sends to the professor.
"""
from __future__ import annotations
import os, sys, time, traceback

from . import config as _cfg
_cfg.load_env_file()

from .sources import arxiv, semantic_scholar as s2, recruiting
from .drafters import cold_email
from .outputs import mailer
from . import projects
from . import outreach_log
from . import hook
from . import programs
from . import regions
from . import followups
from . import freshness
from . import scholarships
from .outputs import imap_ingest


def _area_rotation() -> list[str]:
    areas = _cfg.load_profile().research_areas or []
    if not areas:
        return ["nlp", "ai4health", "cv", "africa", "ml", "nlp", "ai4health"]
    # pad/repeat to 7 for weekday indexing
    return (areas * ((7 // len(areas)) + 1))[:7]


def _pick_senior_author(authors: list[str]) -> tuple[str, str] | None:
    if not authors: return None
    pi = authors[-1].strip()
    parts = pi.split()
    if len(parts) < 2: return None
    return pi, parts[-1]


def _candidate_from_paper(paper: dict) -> dict | None:
    pick = _pick_senior_author(paper.get("authors", []))
    if not pick: return None
    prof_full, prof_last = pick
    # Identity-safe resolution: anchor on the trigger paper's authorId when
    # possible, validated name search otherwise, ambiguous -> skip.
    v = s2.resolve_author(prof_full,
                          arxiv_id=paper.get("arxiv_id", ""),
                          paper_title=paper.get("title", ""))
    if not v.get("ok"):
        return {"prof_full": prof_full, "prof_last": prof_last, "verify": v, "skip": True}
    return {"prof_full": prof_full, "prof_last": prof_last, "verify": v, "skip": False}


def run_batch(n: int = 3, area: str | None = None, dry_run: bool = False) -> dict:
    day_idx = int(time.strftime("%w"))
    rotation = _area_rotation()
    area = area or rotation[day_idx % len(rotation)]

    try:
        papers = arxiv.search(area, max_results=60)
    except Exception as e:
        return {"error": f"arxiv search failed for {area}: {e}"}

    profile = _cfg.load_profile()
    target_regions = profile.target_regions or []

    # Auto-detect replies before anything else, so today's stats and
    # follow-up list reflect the latest inbox state. Best effort.
    try:
        imap_result = imap_ingest.ingest()
    except Exception as e:
        imap_result = {"error": str(e)}

    # Learned bias: projects that earned replies rank up in matching.
    try:
        boost = outreach_log.project_response_boost()
    except Exception:
        boost = {}

    drafts: list[dict] = []
    skipped: list[dict] = []
    seen_this_run: set[str] = set()

    for paper in papers:
        if len(drafts) >= n: break
        cand = _candidate_from_paper(paper)
        if not cand: continue
        prof_full = cand["prof_full"]; prof_last = cand["prof_last"]
        if prof_full in seen_this_run: continue
        seen_this_run.add(prof_full)
        if cand["skip"]:
            reason = cand["verify"].get("reason") or "verification failed"
            stage = "identity" if "ambiguous" in reason else "faculty-gate"
            skipped.append({"prof": prof_full, "why": reason})
            outreach_log.add_skip(prof_full, stage, reason, source="daily",
                                  area=area, paper_title=paper.get("title", ""),
                                  arxiv_id=paper.get("arxiv_id", ""),
                                  resolution=cand["verify"].get("resolution", ""))
            continue

        v = cand["verify"]
        affiliation = v.get("affiliations", [""])[0] if v.get("affiliations") else ""

        # Dedup on the canonical S2 authorId, name fallback for legacy rows.
        if outreach_log.already_contacted(prof_full, affiliation,
                                          author_id=v.get("author_id")):
            outreach_log.add_skip(prof_full, "dedup", "already contacted",
                                  source="daily", area=area,
                                  paper_title=paper.get("title", ""),
                                  arxiv_id=paper.get("arxiv_id", ""),
                                  resolution=v.get("resolution", ""))
            continue

        # Region gate. Unknown regions pass through flagged, never dropped.
        region_ok, region = regions.allowed(affiliation, target_regions,
                                            homepage=v.get("homepage") or "")
        if not region_ok:
            reason = f"outside target regions ({region}: {affiliation})"
            skipped.append({"prof": prof_full, "why": reason})
            outreach_log.add_skip(prof_full, "region", reason, source="daily",
                                  area=area, paper_title=paper.get("title", ""),
                                  arxiv_id=paper.get("arxiv_id", ""),
                                  resolution=v.get("resolution", ""))
            continue

        # Recent papers for the multi-paper hook
        recents = s2.recent_papers(v["author_id"], limit=5) or [paper]
        # Ensure the trigger paper is present at top
        titles = {p.get("title","").lower() for p in recents}
        if paper.get("title","").lower() not in titles:
            recents = [paper] + recents

        # Recruiting + email
        rec = recruiting.signal(v.get("homepage") or "")

        # Match project (with learned outcome boost)
        surface = " ".join(p.get("title","") + " " + (p.get("abstract") or "") for p in recents[:2])
        match = projects.best_project(recents[0].get("title",""), surface, area,
                                      outcome_boost=boost)

        # Hook (multi-paper + verify)
        h = hook.build(
            papers=recents[:3],
            project_name=match["name"],
            project_pitch=match["pitch"],
            project_tags=match.get("tags", []),
        )

        # Fit score: one cheap call so the user can triage drafts in seconds.
        fit = hook.fit_score(recents[:3], match["name"], match["pitch"])

        # Freshness warnings (never gates): current lab + recent activity.
        aff_fresh = freshness.affiliation_check(affiliation, rec.get("page_text", ""))
        act_fresh = freshness.activity_check(recents)

        # Program suggestion
        prog_hits = programs.match_faculty(prof_full)
        prog_line = prog_hits[0]["id"] if prog_hits else ""

        d = cold_email.build(
            prof_name=prof_full, prof_lastname=prof_last,
            university=v.get("affiliations", [""])[0] if v.get("affiliations") else "",
            their_paper_title=recents[0].get("title",""),
            substantive_hook=h["hook"],
            your_project_name=match["name"],
            your_project_link=match["link"],
            target_term="Fall 2027",
            degree=("PhD" if any(pg["degree"]=="PhD" for pg in prog_hits) else "MSc"),
        )
        drafts.append({
            "prof_name": prof_full, "prof_lastname": prof_last,
            "paper_title": recents[0].get("title",""),
            "paper_url": recents[0].get("url",""),
            "area": area,
            "region": region,
            "project_matched": match["name"],
            "match_score": match["score"],
            "matched_tags": match.get("matched_tags", []),
            "outcome_boost": match.get("outcome_boost", 0),
            "fit": fit,
            "aff_fresh": aff_fresh,
            "act_fresh": act_fresh,
            "hook_source": h["source"],
            "hook_attempts": h.get("attempts", 1),
            "hook_verdict": h.get("verification", {}).get("verdict", ""),
            "verify": v,
            "recruiting": rec,
            "program_id": prog_line,
            "email": d,
        })

    # Log
    for d in drafts:
        v = d["verify"]; rec = d["recruiting"]
        outreach_log.add(
            prof_name=d["prof_name"], prof_lastname=d["prof_lastname"],
            prof_email=(rec.get("email") or ""),
            university=(v.get("affiliations", [""])[0] if v.get("affiliations") else ""),
            program_target=d.get("program_id",""),
            area=d["area"], paper_title=d["paper_title"], paper_url=d["paper_url"],
            project_matched=d["project_matched"], match_score=d["match_score"],
            email_subject=d["email"]["subject"],
            review_mail_sent_at=time.strftime("%Y-%m-%d %H:%M"),
            s2_hindex=v.get("h_index"), s2_papers=v.get("paper_count"),
            affiliation=(v.get("affiliations", [""])[0] if v.get("affiliations") else ""),
            homepage=v.get("homepage") or "",
            recruiting_signal=("yes" if rec.get("recruiting") else "no" if rec.get("recruiting") is False else "unknown"),
            hook_attempts=d["hook_attempts"], hook_verdict=d["hook_verdict"],
            s2_author_id=v.get("author_id") or "",
            region=d.get("region", ""),
            fit_score=d.get("fit", {}).get("score", ""),
            fit_reason=d.get("fit", {}).get("reason", ""),
        )

    # Best fit first, so the strongest draft is the first thing read.
    drafts.sort(key=lambda d: -(d.get("fit", {}).get("score") or 0))

    # Compose review email
    deadlines = programs.upcoming_deadlines(45)
    region_note = f"  Regions: {', '.join(target_regions)}" if target_regions else ""
    lines = [
        f"Daily outreach batch, area: {area}{region_note}",
        f"Date: {time.strftime('%Y-%m-%d')}",
        f"Drafted: {len(drafts)}  Skipped: {len(skipped)}",
        "",
    ]
    if imap_result.get("replies_found"):
        lines.append(f"NEW REPLIES DETECTED (via IMAP): {', '.join(imap_result['tagged'])}")
        lines.append("")
    followup_lines = followups.review_email_section(days=10)
    if followup_lines:
        lines += followup_lines
    # Outcome feedback: what your tagged responses say is working.
    try:
        stats = outreach_log.outcome_stats()
        if stats["total_sent"] > 0:
            lines.append(
                f"OUTCOMES SO FAR: {stats['total_sent']} sent, "
                f"{stats['total_responded']} responded")
            for proj, a in sorted(stats["by_project"].items(),
                                  key=lambda kv: -kv[1]["response_rate"])[:5]:
                lines.append(
                    f"  {proj}: {a['responded']}/{a['sent']} replies "
                    f"({int(a['response_rate']*100)}%)")
            if boost:
                lines.append(f"  Matching bias applied: {boost}")
            lines.append("")
    except Exception:
        pass
    if deadlines:
        lines.append("UPCOMING PROGRAM DEADLINES (next 45 days):")
        for d in deadlines:
            lines.append(f"  {d['days_left']:>3}d  {d['deadline']}  {d['program']}  {d['university']}")
        lines.append("")
    try:
        sch = scholarships.upcoming_deadlines(60)
        if sch:
            lines.append("UPCOMING SCHOLARSHIP DEADLINES (next 60 days):")
            for s in sch:
                lines.append(f"  {s['days_left']:>3}d  {s['deadline']}  {s['name']}")
            lines.append("")
    except Exception:
        pass
    if skipped:
        lines.append("Skipped candidates (verification fail or outside regions):")
        for s in skipped[:8]:
            lines.append(f"  - {s['prof']}: {s['why']}")
        lines.append("")
    for i, d in enumerate(drafts, 1):
        v = d["verify"]; rec = d["recruiting"]; e = d["email"]
        lines += [
            "=" * 72,
            f"[{i}] {d['prof_name']}  FIT: {d.get('fit', {}).get('score', '?')}/10",
            f"Fit reason: {d.get('fit', {}).get('reason', '')}",
            f"Affiliation: {(v.get('affiliations') or ['unknown'])[0]}  [region: {d.get('region', 'unknown')}]",
            f"Identity: {v.get('resolution', 'name-search')}",
            f"Freshness: {d.get('aff_fresh', {}).get('note', '')}  |  {d.get('act_fresh', {}).get('note', '')}",
            f"h-index: {v.get('h_index')}  papers: {v.get('paper_count')}",
            f"Homepage: {v.get('homepage') or '(none on S2 profile)'}",
            f"Recruiting signal: {'YES ' + ', '.join(rec.get('matched', [])[:2]) if rec.get('recruiting') else 'no'}",
            f"Best email guess: {rec.get('email') or '(verify manually)'}",
            f"Paper: {d['paper_title']}",
            f"URL: {d['paper_url']}",
            f"Matched project: {d['project_matched']} (score {d['match_score']}, tags: {', '.join(d['matched_tags'][:5])})",
            f"Program lead: {d['program_id'] or '(no seeded program lists them)'}",
            f"Hook: {d['hook_source']}  attempts={d['hook_attempts']}  verdict={d['hook_verdict']}",
            "",
            f"Subject: {e['subject']}",
            "",
            e["body"],
            "",
        ]

    body = "\n".join(lines) if lines else "no drafts today"
    prof_cfg = _cfg.load_profile()
    cv = prof_cfg.cv_path or os.environ.get("CV_PATH", "")
    transcript = prof_cfg.transcript_path or os.environ.get("TRANSCRIPT_PATH", "")
    attachments = [p for p in (cv, transcript) if p and os.path.exists(p)]

    if dry_run:
        return {"area": area, "drafted": len(drafts), "skipped": len(skipped),
                "preview": body[:3000]}
    if not drafts:
        return {"area": area, "drafted": 0, "skipped": len(skipped),
                "note": "no verified candidates today"}
    res = mailer.send_to_me(
        subject=f"Daily outreach ({area}) {time.strftime('%Y-%m-%d')}, {len(drafts)} drafts",
        body=body, attachments=attachments,
    )
    return {"area": area, "drafted": len(drafts), "skipped": len(skipped),
            "mail": res, "deadlines_flagged": len(deadlines)}


if __name__ == "__main__":
    try:
        n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    except ValueError:
        n = 3
    try:
        print(run_batch(n=n))
    except Exception:
        traceback.print_exc(); sys.exit(1)
