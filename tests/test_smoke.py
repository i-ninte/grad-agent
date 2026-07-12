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
