# grad-agent

<!-- mcp-name: io.github.i-ninte/grad-agent -->

An autonomous MCP agent that helps you apply to fully funded MS and PhD programs.

- Discovers professors on arXiv in your research areas
- Verifies each candidate is actually faculty (Semantic Scholar, h-index, papers)
- Scrapes their lab page for a recruiting signal + email address
- Matches them to your strongest shipped project
- Drafts a specific, fact-checked cold email (Claude Haiku authors + verifies claims against paper abstracts)
- Compiles a per-school SOP to PDF (LaTeX)
- Tracks everything in xlsx: outreach, LOR requests, program deadlines
- Emails every draft to your inbox for review; nothing is sent to a professor without you

Runs as a stdio MCP server for Claude Code / Claude Desktop, or as a plain CLI.

## Install

```bash
pipx install grad-agent
# or, if you prefer pip in a venv
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
- `~/.grad-agent/.env` — secrets template

Fill in `~/.grad-agent/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=<gmail app password>
SMTP_FROM=you@gmail.com
# Optional:
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
- `seed_projects:` 3 to 10 flagship projects with `name`, `pitch`, `link`, `tags`

Then:

```bash
grad-agent sync        # scan projects (GitHub + HF + local)
grad-agent run         # one batch, drafts land in your inbox
```

## Register with Claude Code

```bash
grad-agent register-claude
```

Prints the exact `claude mcp add` command. Once registered, `/mcp` in Claude Code shows `grad-agent` with ~25 tools.

## Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "grad-agent": {
      "command": "grad-agent",
      "args": ["server"]
    }
  }
}
```

## Daily autonomous run (macOS)

The package ships a launchd plist template. To fire every day at 08:00:

```bash
cp /path/to/grad_agent/templates/com.gradagent.daily.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.gradagent.daily.plist
```

Every morning: 3 verified faculty leads, hooks fact-checked against paper abstracts, in your inbox for review.

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
| `draft_cold_email(...)` | Manual per-prof draft |
| `draft_sop(...)` | Compile a Columbia-style SOP PDF for one school |
| `send_draft_to_me(path)` | Ship any draft file to your review inbox |
| `discover_profs(area)` | arXiv + OpenReview scan (raw candidates, no verification) |

Blog publishing tools (`publish_article`, `update_article`, ...) are gated behind `blog.enabled: true` in `profile.yaml` and are specific to the author's Turso-backed Next.js portfolio. Most users can ignore them.

## What the agent will not do

- Send any email to a professor. Every send is manual, from your Gmail, after you read the draft.
- Fabricate a paper claim. The hook goes through a second Claude call that rejects any claim not present in the abstracts, and rewrites.
- Draft for programs you are ineligible for. If your `degree_status` is `bachelors`, PhD programs that require an MSc first are filtered out.

## Requirements

- Python 3.10+
- macOS or Linux (Windows untested)
- `pdflatex` on PATH if you want SOP PDFs (macOS: MacTeX; Ubuntu: `texlive-latex-recommended`)
- Anthropic API key
- Gmail (or another SMTP) for the review-mailer

## Where your data lives

Everything is under `~/.grad-agent/` by default, or `$GRAD_AGENT_HOME` if set:

```
~/.grad-agent/
  profile.yaml         identity + preferences
  programs.yaml        target programs
  .env                 secrets (gitignored)
  data/
    outreach_log.xlsx  every prof surfaced or drafted
    lor_log.xlsx       recommendation-letter tracker
    catalog.json       synced projects (GitHub + HF + local)
    db.sqlite          drafts + status
  drafts/              per-school SOP + email drafts
```

## Contributing

MIT licensed. PRs welcome for: more program templates, non-Gmail SMTP presets, non-arXiv source adapters, and better prof-verification heuristics.

## Author

Kwabena Obeng · [i-ninte.github.io/portfolio/](https://i-ninte.github.io/portfolio/)
