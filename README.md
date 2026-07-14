# grad-agent

<!-- mcp-name: io.github.i-ninte/grad-agent -->

An autonomous MCP agent that helps you apply to fully funded MS and PhD programs.

**Discover and draft**

- Discovers professors on arXiv in your research areas, or deadline-driven per program (`run_program_batch`)
- Resolves each professor's identity by anchoring on the trigger paper's canonical Semantic Scholar authorId, not the name string — name collisions like "Wei Zhang" are structurally impossible to confuse
- Refuses to draft when identity cannot be anchored; the specific mismatch (e.g. `identity ambiguous: 2 comparable candidates, h=40 vs h=38`) is persisted to a `skipped` sheet for audit
- Verifies each candidate is actually faculty (h-index and paper-count gates)
- Filters by region (`target_regions: [US, Canada]` in your profile; keyword table + homepage TLD + LLM fallback)
- Scrapes their lab page for a recruiting signal + email address
- Matches them to your strongest shipped project (tag overlap + TF-IDF semantic layer + learned response-rate bias)
- Drafts a specific, fact-checked cold email: Claude Haiku writes a hook spanning the prof's recent papers, then a second call verifies every claim against the abstracts and rewrites anything unsupported
- Scores each draft 1 to 10 for fit, with a one-line reason, so you can triage in seconds
- **Freshness warnings** on every draft: cross-checks the S2 affiliation against the prof's live homepage (flags `MISMATCH` if they may have moved labs) and flags researchers who have not published in 2+ years

**Learn and follow through**

- Detects professor replies via read-only IMAP and tags the log automatically
- Learns from outcomes: projects that earn replies rank up in future matching (`outcome_report` shows what works)
- Drafts follow-up nudges for profs silent 10+ days; never nudges the same prof twice
- Generates an interview prep one-pager when a prof replies: their papers summarised, likely questions, your talking points

**Track everything**

- Compiles per-school SOPs to PDF (LaTeX), versioned so no draft is ever overwritten
- Tracks outreach, LOR requests, program deadlines, and external scholarships (Mastercard, Commonwealth, Fulbright, Rhodes, and more) in xlsx/yaml
- Emails every draft to your inbox for review; nothing is ever sent to a professor without you

Runs as a stdio MCP server for Claude Code / Claude Desktop / any MCP client, or as a plain CLI.

Published on:

- **PyPI**: [`grad-agent`](https://pypi.org/project/grad-agent/)
- **MCP Registry**: [`io.github.i-ninte/grad-agent`](https://registry.modelcontextprotocol.io/v0/servers?search=io.github.i-ninte/grad-agent)

## Install

Pick one:

```bash
# Recommended for MCP clients (Claude Desktop, Claude Code, etc.)
uvx grad-agent server      # single-shot, no persistent install

# Persistent CLI install
pipx install grad-agent

# Or in a venv
python3 -m venv .venv && source .venv/bin/activate
pip install grad-agent
```

## Set up in 5 minutes

```bash
grad-agent init
```

This writes:

- `~/.grad-agent/profile.yaml` — your identity, projects, preferences
- `~/.grad-agent/programs.yaml` — target programs (seeded)
- `~/.grad-agent/scholarships.yaml` — external scholarships with deadlines (seeded)
- `~/.grad-agent/.env` — secrets template

Fill in `~/.grad-agent/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
SMTP_SERVER=smtp.gmail.com        # presets for Outlook/Yahoo/Zoho in the template
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=<gmail app password>
SMTP_FROM=you@gmail.com
# Optional:
S2_API_KEY=                       # free Semantic Scholar key, dedicated rate limits
                                  # (client-side throttle already enforces >=1.1s between requests)
IMAP_SERVER=imap.gmail.com        # read-only reply detection; defaults to SMTP creds
GITHUB_USERNAME=your-gh
GITHUB_TOKEN=github_pat_...
HF_USERNAME=your-hf
```

Fill in the important bits of `~/.grad-agent/profile.yaml`:

- `name`, `identity_line`, `portfolio`
- `cv_path`, `transcript_path` (absolute paths)
- `degree_status: bachelors | masters` (drives PhD eligibility gating)
- `target_term`, `target_degree`
- `research_areas: [nlp, ai4health, ...]`
- `target_regions: [US, Canada]` — only draft for profs in these regions (empty = anywhere)
- `seed_projects:` 3 to 10 flagship projects with `name`, `pitch`, `link`, `tags`

Profile edits apply immediately, even while a long-running MCP session is open.

Then:

```bash
grad-agent sync        # scan projects (GitHub + HF + local)
grad-agent run         # one batch, drafts land in your inbox
```

## Register with Claude Code

Three commands, in order:

```bash
pipx install grad-agent
pipx ensurepath                              # macOS/Linux: opens ~/.local/bin on PATH
                                             # Windows: opens %USERPROFILE%\.local\bin on PATH
claude mcp add grad-agent grad-agent server
```

On Windows you may need to open a new PowerShell or Terminal window after
`pipx ensurepath` for the PATH change to take effect.

Prefer a zero-install one-liner? Skip `pipx` and use `uvx`:

```bash
claude mcp add grad-agent uvx grad-agent server
```

Then in a **new** Claude Code session:

```
/mcp
```

You should see `grad-agent` connected with ~36 tools. Before it does anything useful, run `grad-agent init` (or `uvx grad-agent init`) and fill in `~/.grad-agent/.env` and `~/.grad-agent/profile.yaml` as described in the setup section above.

If you skipped `pipx ensurepath`, `grad-agent register-claude` prints an absolute-path variant of the command that works without PATH changes.

## Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "grad-agent": {
      "command": "uvx",
      "args": ["grad-agent", "server"]
    }
  }
}
```

The `uvx` command needs no prior install. If you already ran `pipx install grad-agent`,
you can use `"command": "grad-agent", "args": ["server"]` instead.

Any other MCP client (Cursor, Zed, Windsurf) uses the same manifest shape; just
point them at `uvx grad-agent server`.

## Daily autonomous run

The package ships scheduler templates for all three OSes. `grad-agent schedule`
emits the right one for your platform:

```bash
grad-agent schedule --dest .
```

Then follow the install instructions the command prints. In case you want them
up front:

**macOS (launchd):**

```bash
cp com.gradagent.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.gradagent.daily.plist
```

**Linux (systemd user timer, fires at 08:00 local):**

```bash
mkdir -p ~/.config/systemd/user
cp grad-agent-daily.service grad-agent-daily.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now grad-agent-daily.timer
```

**Windows (Task Scheduler):**

```powershell
# In an elevated PowerShell prompt:
schtasks /Create /TN "grad-agent-daily" /XML .\grad-agent-daily.xml
```

Or import the XML via the Task Scheduler GUI (Action → Import Task).

Every morning: replies auto-detected via IMAP, follow-up nudges drafted for silent profs, 3 identity-verified faculty leads with fit scores (best fit first), hooks fact-checked against paper abstracts, freshness warnings when a prof's S2 record and live homepage disagree, plus program and scholarship deadline warnings — all in one review email. Skipped leads are persisted with the specific mismatch reason (view with `skipped_log_view` or open the `skipped` sheet).

## What each MCP tool does

| Tool | Purpose |
|---|---|
| `run_daily_batch(n, area)` | Full pipeline: verify → recruiting → hook + verify → draft → log |
| `outreach_log_view(limit)` | Show last N rows of the outreach xlsx |
| `outreach_mark_sent(prof, uni)` | Flag a row as actually sent to the prof |
| `sync_catalog(source)` | Pull projects from `github`, `hf`, or `local` |
| `list_projects_in_catalog()` | Show every project the matcher can see |
| `list_programs()` | Your target programs |
| `upcoming_deadlines(days)` | Any program deadline in the next N days |
| `lor_add / lor_outstanding / lor_mark` | Recommendation-letter tracker |
| `run_program_batch(program_id, n)` | Deadline-driven batch: draft for one program's faculty |
| `skipped_log_view(limit)` | Audit trail of skipped leads with the specific stage + mismatch reason |
| `s2_cache_invalidate(query, all)` | Selectively purge Semantic Scholar cache entries by author name or id |
| `followups_due(days)` | Drafted nudges for profs silent 10+ days |
| `outreach_mark_followup(prof)` | Record a sent nudge (never nudged twice) |
| `outreach_mark_response(prof, outcome)` | Tag replies; feeds the matcher's learning loop |
| `outcome_report()` | Response rates by area and project |
| `ingest_replies()` | Read-only IMAP scan; auto-tags replies in the log |
| `interview_prep(prof)` | One-page brief: their papers, likely questions, your talking points |
| `list_scholarships(region)` | External scholarships filtered by eligibility region |
| `upcoming_scholarship_deadlines(days)` | Scholarship deadlines approaching |
| `draft_cold_email(...)` | Manual per-prof draft |
| `draft_sop(...)` | Compile a Columbia-style SOP PDF (versioned: sop_v1, v2, ...) |
| `send_draft_to_me(path)` | Ship any draft file to your review inbox |
| `discover_profs(area)` | arXiv + OpenReview scan (raw candidates, no verification) |

Blog publishing tools (`publish_article`, `update_article`, ...) are gated behind `blog.enabled: true` in `profile.yaml` and are specific to the author's Turso-backed Next.js portfolio. Most users can ignore them.

## What the agent will not do

- Send any email to a professor. Every send is manual, from your Gmail, after you read the draft.
- Touch your inbox beyond reading. IMAP access is read-only: it never sends, deletes, or marks messages.
- Fabricate a paper claim. The hook goes through a second Claude call that rejects any claim not present in the abstracts, and rewrites.
- Email the same professor twice. Deduplication is keyed on the Semantic Scholar authorId, with a name fallback for legacy rows, and follow-ups are marked so no prof is nudged more than once.
- Draft for the wrong person when two profs share a name. Identity is resolved from the trigger paper's authorId, not the name string; ambiguous cases are refused and logged.
- Hide why a lead was rejected. Every skip is persisted to the `skipped` sheet in `outreach_log.xlsx` with the stage (identity, faculty-gate, region, dedup, no-papers) and the exact mismatch — not buried in old review emails.
- Exceed Semantic Scholar's rate limit. Client-side throttle enforces ≥1.1s between requests, with exponential backoff on any 429 or 5xx.
- Draft for programs you are ineligible for. If your `degree_status` is `bachelors`, PhD programs that require an MSc first are filtered out. Same gate for scholarships outside your eligibility region.

## Requirements

- Python 3.10+
- macOS, Linux, or Windows (all three tested in CI on 3.10 / 3.11 / 3.12)
- `pdflatex` on PATH if you want SOP PDFs
  (macOS: MacTeX; Ubuntu: `texlive-latex-recommended`; Windows: MiKTeX)
- Anthropic API key
- Gmail (or another SMTP) for the review-mailer

## Where your data lives

Everything is under `~/.grad-agent/` by default, or `$GRAD_AGENT_HOME` if set:

```
~/.grad-agent/
  profile.yaml         identity + preferences (regions, seed projects, ...)
  programs.yaml        target programs with eligibility rules + deadlines
  scholarships.yaml    external scholarships with region eligibility + deadlines
  .env                 secrets (gitignored)
  data/
    outreach_log.xlsx  outreach sheet (drafts + outcomes) + skipped sheet (audit trail)
    lor_log.xlsx       recommendation-letter tracker
    catalog.json       synced projects (GitHub + HF + local)
    s2_cache.json      Semantic Scholar lookups (14 day TTL)
    region_cache.json  LLM-inferred regions for unusual affiliations
    db.sqlite          drafts + status
  drafts/              per-school SOP versions + email drafts
    prep/              interview prep one-pagers
```

## Contributing

MIT licensed. PRs welcome for: more program templates, non-Gmail SMTP presets, non-arXiv source adapters, and better prof-verification heuristics.

## Author

Kwabena Obeng · [i-ninte.github.io/portfolio/](https://i-ninte.github.io/portfolio/)
