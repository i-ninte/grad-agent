---
name: lor-writing
description: Use when drafting a letter of recommendation, especially the common case where the applicant drafts a letter for a recommender to review, sign, and upload. Encodes rules from College Essay Guy, MIT Admissions, CUNY Medicine samples, HHMI, and University of Oregon graduate letters guide. Produces a signed-by-recommender letter that reads human, not templated.
---

# lor-writing

## What a letter of recommendation is FOR

The committee is answering one question: *"Does a credible third party, close to the applicant's work, believe this applicant will do publishable research (or excellent work) in the next 2–6 years — and can they show why?"*

A LOR is **evidence for a claim**, not a certificate of good character. Every paragraph must move that decision. Generic praise ("hardworking, motivated, a joy to work with") is negative signal: it tells the committee the writer did not know the applicant well enough to say something specific.

## When the applicant drafts the letter

This is the common case for MS/PhD, industry-to-grad, and international applications where a busy supervisor asks the candidate to "send me something to sign." The applicant is the ghostwriter; the letter must:

1. Sound like the recommender, not the applicant. Different diction, different sentence rhythm from the applicant's SOP.
2. Say things the applicant could not tell the committee themselves without sounding boastful.
3. Include one or two details only the recommender could plausibly know (a specific meeting, a decision the applicant pushed back on, an incident the recommender witnessed).
4. Corroborate — never repeat — the SOP's research question. If the SOP says X, the letter should give lived, from-the-outside evidence of X.

## Rule set

### 1. Header + salutation
- Recommender name, title, organisation, direct email, date. Physical address optional.
- Address to the specific program committee if known ("To the Graduate Admissions Committee, Department of Computer Science, LMU"). Never "To Whom It May Concern." University of Oregon flags impersonal openings as weaker letters.
- One-line subject: `Letter of Recommendation for <Full Name>`.

### 2. Opening paragraph (60–90 words)
State **relationship**, **duration**, and **one-sentence overall claim** with a superlative bounded by evidence (e.g. "in the top three engineers I have hired in five years, on the basis of X"). No un-anchored superlatives.

Never open with "It is my pleasure to write this letter." Cut that sentence.

### 3. Evidence paragraphs (2–4, ~120–180 words each)

Each paragraph makes **one claim** about the applicant and proves it with a **specific incident**. Formula:

1. Claim (one sentence): *"Kwabena is unusual in that he treats evaluation design as a first-class research object."*
2. Situation the recommender witnessed: what the project was, what the constraint was.
3. The applicant's specific action, with numbers or artifacts: named systems, dataset sizes, percentages, releases, users affected.
4. Result the recommender can vouch for.
5. What that tells you about how they will behave in graduate school.

Cover a mix of dimensions across the paragraphs. Pick 2–4 from:
- Technical depth and independence
- Research taste / question selection
- Written and verbal communication (esp. writing that a committee cares about)
- Mentorship, teamwork, response to feedback
- Response to failure or setback (MIT explicitly asks for this)
- Ethical judgment / handling of sensitive data or user trust

### 4. Comparative statement (mandatory for graduate letters)
One line that places the applicant against a defined peer set. HHMI's guidance: unquantified praise is discounted. Examples:
- *"Of the roughly 20 engineers I have hired at this level in the last five years, he is in the top two."*
- *"He is the strongest self-taught applied-NLP engineer I have worked with in Ghana's small AI industry."*
Only make a comparison the recommender could actually stand behind. If unsure, drop it — a soft comparison is worse than none.

### 5. Fit-and-forecast paragraph
Two to three sentences connecting the applicant's demonstrated behaviour to what the target program specifically demands. Name the program's structural features (thesis, cohort size, compute, specific labs) if you can do so credibly from the recommender's point of view. Say what you expect the applicant to *become* over 2–6 years, not what you hope for.

### 6. Close (40–60 words)
- One-line unqualified recommendation ("I recommend him without reservation" — only if true; otherwise say what qualification you attach).
- Explicit invitation to contact: phone or email, verifiable domain.
- Signature line.

### 7. Length and format
- 1 page, occasionally 1.5. Two pages is the ceiling and only if the recommender is truly senior and has three years-plus with the applicant.
- 11 pt, 1-inch margins. Recommender's letterhead if available. If drafting a version for the recommender to paste onto letterhead, keep the top block plain so it drops in cleanly.
- No em dashes, en dashes, or hyphens as clause separators (essay-compile rule).

**Letterhead / company logo (LaTeX compile).** The `.env` variable `LOR_LETTERHEAD_PATH` points at an image file (`.png`, `.jpg`, or `.pdf`) to embed at the top of the letter. When set, the LaTeX template drops in `\includegraphics[width=<<LOR_LETTERHEAD_WIDTH>>]{<<LOR_LETTERHEAD_PATH>>}` above the recommender's header block; width defaults to `2.2in` and is overridable via `LOR_LETTERHEAD_WIDTH`. When unset, the compile emits a plain top block so the recommender can paste it onto their own letterhead after signing. The template must reference the image via a placeholder like `<<LETTERHEAD_BLOCK>>` that resolves to either the `\includegraphics{...}` line or an empty string — never hardcode a path.

### 8. Voice — human, not corporate

- Short direct sentences. First person from the recommender.
- Land at least one line that would come out of the recommender's mouth in a hallway. A small opinion, a taste, a moment of dry judgment: *"I remember pushing back on his fraud-signal design in a review; he came back the next week with the ablation and won the argument."*
- Show ordinary specifics: room, week, meeting, PR number, dashboard. These are the fingerprints that make a letter feel real.
- No "passionate, dedicated, hardworking." No "team player." No "strong communication skills" as a standalone claim.
- No superlatives about the applicant's future ("will change the world"). Forecast concretely: what venues, what problem class, what role.

### 9. Bias hygiene (HHMI, backed by studies)

- Talk about the work, not the person's personality traits. "Compassionate" and "warm" appear ~2x more in letters for women; letters heavier on personality read as weaker. Balance any character mention with an equal-weight technical or intellectual claim.
- Avoid diminutives ("young man", "kid", "she is a delight to have around").
- Don't discuss family, religion, or non-work adversity unless the applicant has explicitly asked you to.
- Length should match what the recommender knows; a short letter from a distant recommender is honest, a padded letter is not.

### 10. Banned phrases (regex-checkable)

- `\bpassionate\b`, `\bmotivated\b`, `\bhardworking\b`, `\bhard.?working\b`
- `\bteam.?player\b`, `\bjoy to (work with|have)\b`
- `it is (my|a) (great )?pleasure to write`
- `groundbreaking|world.?class|prestigious|renowned|cutting.?edge`
- `strong communication skills` (unless followed by a concrete artifact)
- `will (surely |certainly )?(change|impact|transform) the world`
- `To Whom It May Concern`
- Em dashes / en dashes / hyphens used as clause separators (per essay-compile).

## Workflow when drafting for a recommender to sign

1. Collect from the applicant: target program(s), the applicant's SOP, CV, and 2–4 specific incidents the recommender witnessed. Ask for exact numbers, PR names, dashboards.
2. Match the recommender's actual voice. If you have prior writing by them (a letter they signed for someone else, LinkedIn, blog posts), read it first and mirror sentence length and diction.
3. Draft. Run the banned-phrase sweep.
4. Verify every specific in the letter can be corroborated if the committee calls the recommender. If not, remove it.
5. **Preview before send.** When the applicant is doing the final review, render the PDF and open it locally (`open <pdf>` on macOS) BEFORE mailing. Do not send until the applicant explicitly says "send it." Corrections cost far more once the file is out the door.
6. Send the draft to the recommender with a short note explaining what to change and why. Never send it as a fait accompli.
7. Hand off to `essay-compile` for LaTeX preamble, dash sweep, PDF compile.

## Multi-letter differentiation (when the applicant sends 2+ LORs to the same programme)

Committees read the letters for the same applicant together. If two of them share phrasing, structural moves, or signature anecdote framings, the reader will infer one ghostwriter and both letters lose credibility. Treat differentiation as a first-class requirement, not a stylistic nicety.

Concrete rules:

1. **No shared phrase templates.** If letter A opens the comparative paragraph with "For context, X is a young Ghanaian…" letter B must open its comparative differently in wording and structure. Same for the recommendation close ("I recommend … without reservation. Please feel free to contact me at …") — vary both the recommendation clause and the contact clause.
2. **No shared anecdote framings.** If letter A uses "I pushed back on his X in review; he came back with the ablation" as its evaluation-first proof, letter B cannot reuse the pushback-then-ablation shape even with different technical detail. Pick a different behavioural window (a client interaction, a design tradeoff, a workflow choice for the end user).
3. **Different comparative anchors.** Letter A: "top handful in our hiring pool." Letter B: "strongest contract engineer on this class of engagement." Never repeat the exact peer set framing.
4. **Different faculty and programme-fit sentences.** Rewrite the "why this programme" close in each letter using a different rhetorical move (needs-list vs. becomes-list vs. what-the-programme-lets-him-build).
5. **Match each recommender to what they credibly know.** A hiring CTO can vouch for engineering discipline. A contract CTO can vouch for delivery under a tight window and cross-stack range. A professor can vouch for research question selection. Do not push a claim to a recommender who could not have observed it.
6. Before shipping the second letter, diff the two side by side and flag any sentence over ~10 words that appears in both. Rewrite one.

## Recommender realism (what to leave out even when it strengthens the letter)

Drop anything the specific recommender in real life would not know or bother to say, even if it would technically make the letter stronger:

- **Faculty names at the target programme.** A busy industry CTO who has not been in academic circles will not name-drop three faculty and their subareas. Referring to "a research-focused department" or "the coursework in multilingual NLP" reads truer.
- **Programme structural jargon.** Only cite thesis-based / required-internship / dedicated-compute if the recommender plausibly researched the programme.
- **Sector or business-model context** the recommender was not asked for. If the applicant only said "you don't need to describe the company," strip framing lines like "X is a SaaS company" or "X operates across region Y." Context that the recommender would not volunteer reads as ghostwritten.
- **Papers the recommender did not read.** Never claim admiration for a target-programme professor's paper in a recommender letter.

When in doubt, ask: "Would this specific recommender actually say this at their desk in 15 minutes?" If not, cut.

## Sources encoded in this skill

- College Essay Guy — recommendation writing checklist.
- MIT Admissions — parents & educators guidance on recommendations.
- CUNY School of Medicine — sample recommendation letters (structure).
- HHMI — writing a reference (bias hygiene, comparative statements).
- University of Oregon — graduate letters guide (personalisation, program fit).
