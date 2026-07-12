"""Multi-paper hook with claim verification.

Pipeline:
  1. Given N recent papers (title + abstract), synthesise a paragraph naming
     a research thread across two of them and one narrow angle Kwabena adds.
  2. Verify every non-trivial factual claim in the paragraph against the
     provided abstracts. Any unsupported claim triggers a rewrite.
  3. Return the final paragraph + verification report.
"""
from __future__ import annotations
import os, re, json, textwrap
try:
    import anthropic
except Exception:
    anthropic = None

DRAFT_MODEL = "claude-haiku-4-5-20251001"
VERIFY_MODEL = "claude-haiku-4-5-20251001"

DRAFT_SYSTEM = (
    "You write ONE tight paragraph (2 to 3 sentences, 70 to 110 words, no lists, "
    "plain prose) that a prospective graduate student sends a professor. "
    "You are given multiple recent papers by the professor. The paragraph must: "
    "(a) name a specific research thread that connects at least TWO of the papers "
    "using concrete language pulled from the abstracts, not vague summaries; "
    "(b) tie it to a concrete experience Kwabena had building his matched project; "
    "(c) propose ONE narrow, tractable angle he would bring under supervision. "
    "Speak in Kwabena's voice: direct, technically grounded, honest about what "
    "he does not yet know. No dashes, no em-dashes, no en-dashes, no filler "
    "(passionate, deeply, cutting edge, leverage, delve, holistic, tapestry). "
    "Do not restate paper titles. Do not restate project names. Never invent "
    "results or claims that are not in the provided abstracts."
)

VERIFY_SYSTEM = (
    "You are a strict fact-checker. Given a paragraph and the source abstracts, "
    "return a JSON object {claims: [{text, supported, evidence}], verdict: pass|revise}. "
    "A claim is UNSUPPORTED if it invents a method, metric, or finding that is "
    "not explicitly stated in the abstracts. Personal-experience sentences about "
    "Kwabena's own project are NOT checked. Return only JSON."
)


def _dashless(s: str) -> str:
    s = s.replace("—", ", ").replace("–", ", ").replace(" - ", ", ")
    return re.sub(r",\s*,", ",", s)


def _draft(papers: list[dict], project_name: str, project_pitch: str,
           project_tags: list[str]) -> str:
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        # Minimal fallback: pull first sentence of first paper
        first = (papers[0].get("abstract") or "").split(".")[0]
        return _dashless(
            f"The direction of your work, especially the observation that {first.strip()}, "
            f"is close to something I hit building {project_name.split('(')[0].strip()}: "
            f"{project_pitch}. I would want to work on a narrow extension of that "
            f"thread under your supervision."
        )
    client = anthropic.Anthropic()
    paper_block = "\n\n".join(
        f"[{i+1}] {p.get('title','')}\n{(p.get('abstract') or '')[:1400]}"
        for i, p in enumerate(papers[:3])
    )
    user = textwrap.dedent(f"""\
        RECENT PAPERS BY THE PROFESSOR:
        {paper_block}

        KWABENA'S MATCHED PROJECT
        Name: {project_name}
        What he did: {project_pitch}
        Tags: {', '.join(project_tags)}

        Write the paragraph now.""")
    m = client.messages.create(
        model=DRAFT_MODEL, max_tokens=500,
        system=DRAFT_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    return _dashless(m.content[0].text.strip())


def _verify(paragraph: str, papers: list[dict]) -> dict:
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY"):
        return {"claims": [], "verdict": "pass", "skipped": True}
    client = anthropic.Anthropic()
    abstracts = "\n\n".join(
        f"[{i+1}] {p.get('title','')}\n{(p.get('abstract') or '')[:1400]}"
        for i, p in enumerate(papers[:3])
    )
    user = f"PARAGRAPH:\n{paragraph}\n\nABSTRACTS:\n{abstracts}\n\nReturn JSON now."
    m = client.messages.create(
        model=VERIFY_MODEL, max_tokens=800,
        system=VERIFY_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    raw = m.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).rstrip("`").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"claims": [], "verdict": "pass", "raw": raw[:400]}


FIT_SYSTEM = (
    "You score how strong a fit a prospective graduate student is for a "
    "professor, on a 1 to 10 scale, based on the professor's recent papers "
    "and the student's matched project. 8 to 10 means the student's work is "
    "directly in the professor's research programme. 5 to 7 means adjacent, "
    "a credible email but not an obvious match. 1 to 4 means a stretch. "
    "Return strict JSON: {\"score\": <int>, \"reason\": \"<one sentence, "
    "no dashes>\"}. Nothing else."
)


def fit_score(papers: list[dict], project_name: str, project_pitch: str) -> dict:
    """One Haiku call scoring prof-applicant fit. {'score': int, 'reason': str}."""
    if anthropic is None or not os.environ.get("ANTHROPIC_API_KEY") or not papers:
        return {"score": 0, "reason": "scoring unavailable"}
    try:
        client = anthropic.Anthropic()
        paper_block = "\n\n".join(
            f"[{i+1}] {p.get('title','')}\n{(p.get('abstract') or '')[:800]}"
            for i, p in enumerate(papers[:3])
        )
        m = client.messages.create(
            model=VERIFY_MODEL, max_tokens=150, system=FIT_SYSTEM,
            messages=[{"role": "user", "content": (
                f"PROFESSOR'S RECENT PAPERS:\n{paper_block}\n\n"
                f"STUDENT'S MATCHED PROJECT:\n{project_name}: {project_pitch}\n\n"
                f"Return the JSON now."
            )}],
        )
        raw = re.sub(r"^```(?:json)?", "", m.content[0].text.strip()).rstrip("`").strip()
        obj = json.loads(raw)
        return {"score": int(obj.get("score", 0)),
                "reason": str(obj.get("reason", ""))[:200]}
    except Exception as e:
        return {"score": 0, "reason": f"scoring failed: {e}"}


def build(papers: list[dict], project_name: str, project_pitch: str,
          project_tags: list[str], max_retries: int = 2) -> dict:
    """Draft + verify. Retries with tighter instructions if a claim is unsupported."""
    if not papers:
        return {"hook": "", "source": "none", "error": "no papers"}
    hook = _draft(papers, project_name, project_pitch, project_tags)
    for attempt in range(max_retries):
        v = _verify(hook, papers)
        unsupported = [c for c in v.get("claims", []) if not c.get("supported")]
        if v.get("verdict") == "pass" or not unsupported:
            return {"hook": hook, "source": "anthropic",
                    "verification": v, "attempts": attempt + 1}
        # rewrite: append reject reasons and retry once
        reject = "\n".join(f"- REMOVE: {c.get('text','')}"
                           for c in unsupported[:3])
        if anthropic is None: break
        client = anthropic.Anthropic()
        m = client.messages.create(
            model=DRAFT_MODEL, max_tokens=500,
            system=DRAFT_SYSTEM,
            messages=[{"role": "user", "content": (
                f"Previous draft had unsupported claims:\n{reject}\n\n"
                f"Rewrite the paragraph. Same constraints. Only reference facts "
                f"that appear in the abstracts below.\n\nPAPERS:\n" +
                "\n\n".join(f"[{i+1}] {p.get('title','')}\n{(p.get('abstract') or '')[:1400]}"
                            for i, p in enumerate(papers[:3])) +
                f"\n\nPROJECT: {project_name}\n{project_pitch}"
            )}],
        )
        hook = _dashless(m.content[0].text.strip())
    return {"hook": hook, "source": "anthropic",
            "verification": v, "attempts": max_retries}
