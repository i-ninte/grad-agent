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
5. Send the draft to the recommender with a short note explaining what to change and why. Never send it as a fait accompli.
6. Hand off to `essay-compile` for LaTeX preamble, dash sweep, PDF compile.

## Sources encoded in this skill

- College Essay Guy — recommendation writing checklist.
- MIT Admissions — parents & educators guidance on recommendations.
- CUNY School of Medicine — sample recommendation letters (structure).
- HHMI — writing a reference (bias hygiene, comparative statements).
- University of Oregon — graduate letters guide (personalisation, program fit).
