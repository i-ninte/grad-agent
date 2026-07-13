"""Offline smoke tests. Do not hit the network. Do not send email.

These verify that:
  1. Every top-level module imports cleanly.
  2. The dashless scrubber + banned-phrase filter behave as advertised.
  3. Project scoring returns a non-empty ranking against a stub abstract.
  4. Program eligibility gate blocks PhD when degree_status=bachelors.
  5. Cold email drafter produces a subject + body + word count.
  6. SOP LaTeX template renders (no pdflatex required).
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

import pytest


# Force GRAD_AGENT_HOME to a temp dir so we do not touch the user's real state.
@pytest.fixture(autouse=True, scope="session")
def _tmp_home(tmp_path_factory):
    d = tmp_path_factory.mktemp("grad-home")
    (d / "data").mkdir()
    (d / "drafts").mkdir()
    # Minimal profile so drafters can read defaults without failing
    (d / "profile.yaml").write_text(
        "name: Test User\n"
        "identity_line: a test applicant\n"
        "portfolio: https://example.com\n"
        "degree_status: bachelors\n"
        "target_term: Fall 2027\n"
        "target_degree: PhD\n"
        "research_areas: [nlp]\n"
        "review_email: test@example.com\n"
        "seed_projects:\n"
        "  - name: DummyNLP\n"
        "    pitch: a dummy nlp pitch used in unit tests\n"
        "    link: https://example.com/dummy\n"
        "    tags: [nlp, llm, evaluation, retrieval, low resource]\n"
    )
    (d / "programs.yaml").write_text(
        "- id: needs_msc\n"
        "  university: Test U\n"
        "  degree: PhD\n"
        "  direct_entry: false\n"
        "  requires_masters_before_phd: true\n"
        "  deadline: '2099-12-01'\n"
        "  affiliated_faculty: []\n"
        "- id: direct\n"
        "  university: Direct U\n"
        "  degree: PhD\n"
        "  direct_entry: true\n"
        "  requires_masters_before_phd: false\n"
        "  deadline: '2099-11-01'\n"
        "  affiliated_faculty: [Ada Lovelace]\n"
    )
    os.environ["GRAD_AGENT_HOME"] = str(d)
    yield d


def test_imports():
    from grad_agent import (
        config, cli, projects, programs, hook, tracker, lor,
        outreach_log, catalog_sync, daily_run,
    )
    from grad_agent.drafters import cold_email, sop_latex
    from grad_agent.outputs import mailer
    from grad_agent.sources import (
        arxiv, semantic_scholar, recruiting, github, hf, openreview, websearch,
    )
    assert config.home().exists()


def test_dashless_scrub():
    from grad_agent.drafters.cold_email import _strip_dashes, _scrub
    assert "—" not in _strip_dashes("A — B")
    assert "–" not in _strip_dashes("A – B")
    _, banned = _scrub("I am passionate about deeply reaching out.")
    assert set(banned) >= {"passionate", "deeply", "reaching out"}


def test_project_ranking():
    from grad_agent import projects
    ranked = projects.rank_projects(
        prof_paper_title="Low resource evaluation for LLMs",
        prof_paper_abstract="We evaluate retrieval and low resource NLP.",
        area="nlp", top_k=3,
    )
    assert ranked, "expected at least one ranked project"
    assert any(p["name"] == "DummyNLP" for p in ranked)


def test_program_eligibility_gate():
    from grad_agent import programs
    all_p = programs.all_programs()
    by_id = {p["id"]: p for p in all_p}
    # degree_status is bachelors in the fixture profile
    assert programs.eligibility(by_id["needs_msc"])["eligible"] is False
    assert programs.eligibility(by_id["direct"])["eligible"] is True
    hits = programs.match_faculty("Ada Lovelace")
    assert any(h["id"] == "direct" for h in hits)


def test_cold_email_dashless_and_short():
    from grad_agent.drafters import cold_email
    out = cold_email.build(
        prof_name="Ada Lovelace", prof_lastname="Lovelace",
        university="Direct U",
        their_paper_title="Analytical engines",
        substantive_hook="One concrete sentence about the paper. One about my project. One about the extension I would bring.",
        your_project_name="DummyNLP",
        your_project_link="https://example.com/dummy",
    )
    assert out["ok"]
    assert not out["has_dashes"]
    assert out["banned_hits"] == []
    assert out["word_count"] < 210
    assert "Lovelace" in out["body"]
    assert "Analytical engines" in out["body"]


def test_region_inference():
    from grad_agent import regions
    # keyword table hits (no network, no LLM)
    assert regions.infer("McGill University") == "Canada"
    assert regions.infer("Carnegie Mellon University") == "US"
    assert regions.infer("University of Edinburgh") == "UK"
    assert regions.infer("KNUST, Kumasi") == "Africa"
    # empty target list allows everything
    ok, region = regions.allowed("Stanford University", [])
    assert ok and region == "US"
    # region filter blocks out-of-region
    ok, _ = regions.allowed("University of Tokyo", ["US", "Canada"])
    assert not ok
    # alias normalisation
    ok, _ = regions.allowed("MIT", ["usa"])
    assert ok


def test_outreach_dedup_by_author_id_and_name_variant():
    import os
    from grad_agent import outreach_log
    # fresh log inside the tmp GRAD_AGENT_HOME
    p = outreach_log._path()
    if p.exists():
        os.remove(p)
    outreach_log.add(prof_name="David Ifeoluwa Adelani", s2_author_id="12345",
                     area="nlp", project_matched="DummyNLP")
    # exact authorId match
    assert outreach_log.already_contacted("Someone Else", author_id="12345")
    # name-variant match (middle name dropped)
    assert outreach_log.already_contacted("David Adelani")
    # different person, different id
    assert not outreach_log.already_contacted("Ada Lovelace", author_id="99")


def test_region_tld_fallback():
    from grad_agent import regions
    # affiliation missed by the keyword table, homepage TLD resolves it
    assert regions._from_tld("https://cs.example.ac.uk/~prof") == "UK"
    assert regions._from_tld("https://prof.cs.cornell.edu/") == "US"
    assert regions._from_tld("https://www.univ-obscure.fr/people/x") == "EU"
    assert regions._from_tld("https://someuni.gh/staff") == "Africa"
    assert regions._from_tld("") == ""
    # infer() uses the TLD when keywords fail
    assert regions.infer("Obscure Institute of Things",
                         homepage="https://oit.ac.uk/") == "UK"
    ok, region = regions.allowed("Obscure Institute", ["US"],
                                 homepage="https://oit.edu/~x")
    assert ok and region == "US"


def test_dedup_no_collision_when_both_ids_known():
    import os
    from grad_agent import outreach_log
    p = outreach_log._path()
    if p.exists():
        os.remove(p)
    outreach_log.add(prof_name="Wei Zhang", s2_author_id="111", area="nlp",
                     project_matched="DummyNLP")
    # same normalised name, DIFFERENT authorId: proven distinct, no collision
    assert not outreach_log.already_contacted("Wei Q. Zhang", author_id="222")
    # same authorId: duplicate regardless of name spelling
    assert outreach_log.already_contacted("W. Zhang", author_id="111")
    # candidate without an id: name fallback still protects against re-drafting
    assert outreach_log.already_contacted("Wei Zhang")


def test_outcome_stats_and_boost():
    import os
    from grad_agent import outreach_log
    p = outreach_log._path()
    if p.exists():
        os.remove(p)
    names = ["Alice Alpha", "Bob Beta", "Carol Gamma", "Dan Delta"]
    for i, name in enumerate(names):
        outreach_log.add(prof_name=name, s2_author_id=str(i),
                         area="nlp", project_matched="DummyNLP")
        outreach_log.mark_sent(name)
    outreach_log.mark_response("Alice Alpha", "positive")
    outreach_log.mark_response("Bob Beta", "positive")
    stats = outreach_log.outcome_stats()
    assert stats["total_sent"] == 4
    assert stats["total_responded"] == 2
    assert stats["by_project"]["DummyNLP"]["response_rate"] == 0.5
    boost = outreach_log.project_response_boost(min_sends=3)
    assert boost.get("DummyNLP", 0) >= 1


def test_profile_hot_reload(tmp_path):
    import os
    from grad_agent import config
    home = config.home()
    profile_file = home / "profile.yaml"
    original = profile_file.read_text()
    try:
        assert config.load_profile().name == "Test User"
        profile_file.write_text(original.replace("Test User", "Edited User"))
        # no restart, no cache clear: must pick up the edit immediately
        assert config.load_profile().name == "Edited User"
    finally:
        profile_file.write_text(original)


def test_followups_due_and_nudge():
    import os
    import datetime
    from grad_agent import outreach_log, followups
    p = outreach_log._path()
    if p.exists():
        os.remove(p)
    old = (datetime.datetime.now() - datetime.timedelta(days=15)).strftime("%Y-%m-%d %H:%M")
    fresh = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    outreach_log.add(prof_name="Silent Prof", prof_lastname="Prof",
                     s2_author_id="a1", email_subject="Prospective MSc student",
                     paper_title="A Paper", sent_to_prof_at=old, status="sent")
    outreach_log.add(prof_name="Recent Prof", prof_lastname="Prof2",
                     s2_author_id="a2", sent_to_prof_at=fresh, status="sent")
    outreach_log.add(prof_name="Replied Prof", prof_lastname="Prof3",
                     s2_author_id="a3", sent_to_prof_at=old, status="sent")
    outreach_log.mark_response("Replied Prof", "positive")

    due = followups.build_due(days=10)
    names = [d["prof_name"] for d in due]
    assert "Silent Prof" in names          # 15d silent -> due
    assert "Recent Prof" not in names      # sent today -> not due
    assert "Replied Prof" not in names     # replied -> not due
    nudge = due[0]
    assert nudge["subject"].startswith("Re: ")
    assert "—" not in nudge["body"] and "–" not in nudge["body"]

    # after marking, it drops off the due list
    outreach_log.mark_followup_sent("Silent Prof")
    assert not followups.build_due(days=10)


def test_scholarships_gate_and_deadlines(tmp_path):
    from grad_agent import config, scholarships
    (config.home() / "scholarships.yaml").write_text(
        "- id: africa_only\n"
        "  name: Africa Only Fund\n"
        "  eligibility_regions: [Africa]\n"
        "  deadline: '2099-01-01'\n"
        "- id: open_fund\n"
        "  name: Open Fund\n"
        "  eligibility_regions: [any]\n"
        "  deadline: '2099-01-01'\n"
    )
    ids = {s["id"] for s in scholarships.eligible("Africa")}
    assert ids == {"africa_only", "open_fund"}
    ids_us = {s["id"] for s in scholarships.eligible("US")}
    assert ids_us == {"open_fund"}
    # deadline far in the future: not in a 60 day window
    assert scholarships.upcoming_deadlines(60) == []


def test_tfidf_semantic_score_present():
    from grad_agent import projects
    ranked = projects.rank_projects(
        "Retrieval augmented evaluation for low resource NLP",
        "We study retrieval and evaluation in low resource settings.",
        area="nlp", top_k=3,
    )
    assert ranked and "semantic_score" in ranked[0]


def test_identity_resolution_tiers(monkeypatch):
    from grad_agent.sources import semantic_scholar as s2

    def fake_get(path, params, **kw):
        if path.startswith("/paper/arXiv:1111.11111"):
            return {"authors": [
                {"authorId": "junior1", "name": "Ada Junior"},
                {"authorId": "senior9", "name": "Wei Zhang"},
            ]}
        if path == "/author/senior9":
            return {"authorId": "senior9", "name": "Wei Zhang",
                    "affiliations": ["Test University"], "hIndex": 20,
                    "paperCount": 50, "homepage": None, "url": ""}
        if path == "/author/search":
            return {"data": [
                {"authorId": "big", "name": "John Smith", "hIndex": 40,
                 "paperCount": 200, "affiliations": [], "homepage": None, "url": ""},
                {"authorId": "small", "name": "John Smith", "hIndex": 38,
                 "paperCount": 150, "affiliations": [], "homepage": None, "url": ""},
            ]}
        return None

    monkeypatch.setattr(s2, "_get", fake_get)
    monkeypatch.setattr(s2, "recent_papers", lambda aid, limit=50: [])
    # avoid cross-test cache pollution
    monkeypatch.setattr(s2, "_cache_load", lambda: {})
    monkeypatch.setattr(s2, "_cache_save", lambda c: None)

    # Tier 1: paper-anchored, matched by last name inside the author list
    r = s2.resolve_author("Wei Zhang", arxiv_id="1111.11111", paper_title="X")
    assert r["resolution"] == "paper-anchored"
    assert r["author_id"] == "senior9"
    assert r["ok"]  # h=20, 50 papers, affiliation on record

    # Tier 3: no anchor, validation impossible -> ambiguous, never a guess
    r = s2.resolve_author("John Smith", arxiv_id="", paper_title="Nonexistent Paper")
    assert r["resolution"] == "ambiguous" and not r["ok"]

    # Program resolution: two comparable candidates (h=40 vs 38), no
    # affiliation anchor -> ambiguous rather than dominant
    r = s2.resolve_for_program("John Smith", "Somewhere University")
    assert r["resolution"] == "ambiguous"


def test_program_dominant_candidate(monkeypatch):
    from grad_agent.sources import semantic_scholar as s2

    def fake_get(path, params, **kw):
        if path == "/author/search":
            return {"data": [
                {"authorId": "star", "name": "Rare Name", "hIndex": 30,
                 "paperCount": 100, "affiliations": [], "homepage": None, "url": ""},
                {"authorId": "homonym", "name": "Rare Name", "hIndex": 2,
                 "paperCount": 5, "affiliations": [], "homepage": None, "url": ""},
            ]}
        return None

    monkeypatch.setattr(s2, "_get", fake_get)
    r = s2.resolve_for_program("Rare Name", "Anywhere University")
    assert r["resolution"] == "dominant-candidate"
    assert r["author_id"] == "star"

    # generic words never anchor: 'University' alone must not match
    def fake_get2(path, params, **kw):
        if path == "/author/search":
            return {"data": [
                {"authorId": "a", "name": "N", "hIndex": 10, "paperCount": 30,
                 "affiliations": ["Saarland University"], "homepage": None, "url": ""},
                {"authorId": "b", "name": "N", "hIndex": 9, "paperCount": 28,
                 "affiliations": [], "homepage": None, "url": ""},
            ]}
        return None

    monkeypatch.setattr(s2, "_get", fake_get2)
    r = s2.resolve_for_program("N", "McGill University")
    assert r["resolution"] != "affiliation-anchored"


def test_s2_throttle(monkeypatch):
    from grad_agent.sources import semantic_scholar as s2
    sleeps: list[float] = []
    monkeypatch.setattr(s2.time, "sleep", lambda x: sleeps.append(x))
    monkeypatch.setattr(s2, "_last_request_ts", 0.0)
    s2._throttle()          # first call: long gap since epoch, no sleep
    s2._throttle()          # immediate second call: must sleep ~1.1s
    assert sleeps and sleeps[-1] > 0.9


def test_cache_invalidate(monkeypatch):
    from grad_agent.sources import semantic_scholar as s2
    store = {
        "verify:david adelani": {"ts": 9e12, "value": {}},
        "author:2518906": {"ts": 9e12, "value": {}},
        "verify:yoav artzi": {"ts": 9e12, "value": {}},
    }
    monkeypatch.setattr(s2, "_cache_load", lambda: dict(store))
    saved = {}
    monkeypatch.setattr(s2, "_cache_save", lambda c: saved.update({"v": c}))
    # substring purge removes only matching keys
    assert s2.cache_invalidate("adelani") == 1
    assert "verify:david adelani" not in saved["v"]
    assert "verify:yoav artzi" in saved["v"]
    # empty query without everything flag is refused
    assert s2.cache_invalidate("") == 0
    # everything wipes all
    assert s2.cache_invalidate(everything=True) == 3


def test_skip_log_roundtrip():
    import os
    from grad_agent import outreach_log
    p = outreach_log._path()
    if p.exists():
        os.remove(p)
    outreach_log.add_skip(
        "John Smith", "identity",
        "identity ambiguous: 2 comparable candidates (h=40 vs h=38)",
        source="daily", area="nlp", paper_title="Some Paper",
        arxiv_id="1234.56789", resolution="ambiguous")
    rows = outreach_log.list_skipped()
    assert len(rows) == 1
    r = rows[0]
    assert r["stage"] == "identity"
    assert "h=40 vs h=38" in r["reason"]
    assert r["arxiv_id"] == "1234.56789"


def test_freshness_checks():
    from grad_agent import freshness
    # match: distinctive affiliation word appears on the homepage
    r = freshness.affiliation_check(
        "Cornell University", "Yoav Artzi, Associate Professor at Cornell Tech")
    assert r["match"] is True
    # mismatch: homepage mentions a different institution
    r = freshness.affiliation_check(
        "Saarland University", "David Adelani, Assistant Professor, McGill and Mila")
    assert r["match"] is False and "MISMATCH" in r["note"]
    # unknowns: empty inputs never claim a match
    assert freshness.affiliation_check("", "some page")["match"] is None
    assert freshness.affiliation_check("MIT CSAIL", "")["match"] is None
    # activity
    import datetime
    y = datetime.date.today().year
    assert freshness.activity_check([{"year": y}])["active"] is True
    assert freshness.activity_check([{"year": y - 5}])["active"] is False
    assert freshness.activity_check([])["active"] is None


def test_sop_versioning(tmp_path):
    from grad_agent.drafters import sop_latex
    kwargs = dict(
        university="Test U", university_short="Test U",
        degree_line="PhD in CS", header_left="PS",
        opening="O.", vision_paragraph="V.",
        t1_head="A", t1_body="a.", t2_head="B", t2_body="b.",
        t3_head="C", t3_body="c.", why_university="w.",
        teaching="t.", long_term="l.", out_dir=str(tmp_path),
    )
    r1 = sop_latex.build(**kwargs)
    r2 = sop_latex.build(**kwargs)
    assert r1["version"] == 1 and r2["version"] == 2
    assert r1["tex"].endswith("sop_v1.tex") and r2["tex"].endswith("sop_v2.tex")
    assert (tmp_path / "sop.tex").exists()  # latest mirror


def test_sop_latex_template_renders(tmp_path):
    from grad_agent.drafters import sop_latex
    out = sop_latex.build(
        university="Test U", university_short="Test U",
        degree_line="PhD in Computer Science",
        header_left="Personal Statement, PhD",
        opening="Opening.", vision_paragraph="Vision.",
        t1_head="One", t1_body="One body.",
        t2_head="Two", t2_body="Two body.",
        t3_head="Three", t3_body="Three body.",
        why_university="Why Test U.",
        teaching="Teaching.",
        long_term="Long term.",
        out_dir=str(tmp_path),
    )
    tex = Path(out["tex"]).read_text()
    assert "Personal Statement" in tex
    assert "example.com" in tex  # portfolio URL from fixture profile
    # pdf compile is optional; do not fail CI if pdflatex is absent
