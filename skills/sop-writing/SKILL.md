---
name: sop-writing
description: Use when drafting or editing a graduate-school Statement of Purpose (MS or PhD). Encodes rules synthesized from MIT CommLab EECS, MIT CAPD, Berkeley Grad Div, Harvard GSAS, Stanford, and CS-faculty guides (Cambronero, Chanenson, Lai). Use alongside essay-compile for the LaTeX/PDF/email step.
---

# sop-writing

## What an SOP is FOR

The committee is answering one question: *"Will this applicant do publishable research with one of our faculty in the next 2–6 years?"*
An SOP is a **research story**, not a life story. Every paragraph must move that decision. If a sentence does not, cut it.

## The Rule Set

### 1. Opening — do exactly one of:
- Pose a **concrete research question** you want to work on ("How do we make multilingual LLMs faithful to low-resource morphology?"), or
- One-sentence intro: *who you are, your background, what you are applying for* + the specific research direction.

**Never open with:**
- "Ever since I was a child…" / "From a young age…" / "As long as I can remember…"
- "I was born in…"
- A dictionary definition of the field
- A famous-person quote
- "I am deeply inspired by Prof. X's groundbreaking research"
- Long autobiography

### 2. Structure

**1-page / 600–800 words / 5 paragraphs:**
1. Hook + research direction (60–90w)
2. Research/project #1 (150–200w)
3. Research/project #2 + through-line to ¶1 (150–200w)
4. Fit paragraph, 2–4 named faculty (150–200w)
5. Goals close (60–90w)

**1.5-page / 900–1100 words / 6–7 paragraphs:** add a second project paragraph and, optionally, a skills/teaching/leadership paragraph before the fit paragraph.

Section headings only for ≥1000w statements. Skip for ≤800w.

### 3. Project paragraphs — mandatory formula, in this order

1. **Problem / gap** (one sentence).
2. **Your specific contribution** — active voice: *"I built / I designed / I measured…"*
3. **Outcome, quantified** — dataset size, accuracy delta, users, venue, award, revenue impact.
4. **What you learned** — the intellectual takeaway, not the technical trivia.
5. **How it shaped the next question** — bridge to the research direction in ¶1.

Do not: list coursework, restate GPA, describe internal feelings, or copy the CV.

### 4. Fit paragraph — faculty naming without ranking

- Name **2–4 faculty**. One name reads as inflexible; "anyone" reads as unprepared.
- **Never** write "first choice," "second choice," "primary advisor," "top choice," or rank order them explicitly.
- Use parallel, non-hierarchical phrasing:
  > *"I would like to work with Prof. A on [specific recent paper/direction]. My work on [X] also connects to Prof. B's research on [Y], and to Prof. C's recent work on [Z]."*
- Cite a **specific recent paper or project** per professor, not a lab homepage tagline.
- Show what you *bring*, not just what you'll receive.
- Echo vocabulary from the program's own site.

### 5. Long-term goals paragraph — MS applicants planning a PhD

Two-to-three sentences. Show **progression**, not aspiration alone:

> *"The MS at [Program] is the next step: I want to deepen my foundations in [subarea] under researchers like [names] while producing publishable work in [direction]. I intend to continue to a PhD focused on [refined question], and eventually [research scientist / faculty / applied-research role] where I can [concrete contribution]."*

Rules:
- Name the *reason* the MS is the right rung (coursework + advising access + specific labs/infrastructure).
- Commit to research beyond the degree.
- Avoid: "I want to change the world," "I have always dreamed of a PhD," "I hope to make a difference."
- Do not end with "I am ready to start in [term]" — the application itself makes that clear.

### 6. Voice & tone

- First person, active voice throughout.
- **Evidence before adjective.** Do not say "passionate"; show the 2 a.m. debugging story with a measurable outcome.
- No superlatives about faculty ("groundbreaking," "world-renowned," "visionary").
- Confident but not boastful; concrete numbers do the boasting.
- Short sentences. First person. No filler.

### 7. Length & format

- **Hard cap: 2 pages.** Content past 2 pages is not read.
- Target 500–1000 words for a 1-page SOP; 900–1100 for 1.5 page.
- 11–12 pt, 1-inch margins, single-spaced or 1.15.
- No images, no bullet lists in the body.
- Program-specific word limits override defaults — always check.

### 8. Banned phrases (regex-checkable)

- `ever since (I was )?(a child|young|little)`
- `from a young age` / `as long as I can remember`
- `I was born in`
- `\bpassionate\b` (unless followed within one sentence by concrete evidence)
- `groundbreaking|world.?class|prestigious|renowned|cutting.?edge|visionary`
- `my dream has always been`
- `hard.?working,? motivated`
- `first choice|second choice|top choice|ideal advisor|primary advisor`
- `I read your paper and was (deeply )?inspired`
- `in today('|s) (rapidly )?evolving world`
- `I am ready to start in`
- Em dashes, en dashes, and hyphens used as clause separators (per essay-compile).

### 9. Frequent mistakes to fix on review

1. Life story instead of research story.
2. Only one named professor, or none.
3. Boilerplate reused across schools with mismatched research areas.
4. Passive voice hiding your contribution.
5. Coursework/GPA recitation duplicating the transcript.
6. No stated research question, only vague "interest in AI."
7. Ending with a generic aspiration instead of a concrete next step.
8. Failing to explain *why a PhD* when a job would suffice.
9. Not echoing the program's own vocabulary.

## Workflow

1. Draft or edit body content using the Rule Set above.
2. Run the banned-phrase sweep (regex list in §8).
3. Verify each project paragraph hits all five steps of §3.
4. Verify fit paragraph names 2–4 faculty with parallel phrasing and specific work references.
5. Hand off to `essay-compile` for LaTeX preamble, dash sweep, PDF compile, and email delivery.
