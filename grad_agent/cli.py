"""grad-agent CLI.

Subcommands:
  init          Interactive setup: writes ~/.grad-agent/profile.yaml + .env
  server        Start the MCP stdio server (for `claude mcp add`).
  run           Run today's outreach batch and email the review inbox.
  sync          Sync catalog from GitHub + HuggingFace + local projects_dir.
  register-claude  Print the `claude mcp add` command tailored to this install.
  path          Print resolved GRAD_AGENT_HOME.
"""
from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

from . import config


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    v = input(f"{label}{suffix}: ").strip()
    return v or default


def cmd_init(args: argparse.Namespace) -> int:
    home = config.ensure_home()
    print(f"Setting up grad-agent at {home}\n")

    tmpl_dir = config.TEMPLATES
    profile_dst = config.profile_path()
    env_dst = config.env_path()
    programs_dst = config.programs_path()

    if profile_dst.exists() and not args.force:
        print(f"profile.yaml already exists at {profile_dst}. Use --force to overwrite.")
    else:
        shutil.copy(tmpl_dir / "profile.example.yaml", profile_dst)
        print(f"wrote {profile_dst}")

    if not programs_dst.exists() or args.force:
        shutil.copy(tmpl_dir / "programs.example.yaml", programs_dst)
        print(f"wrote {programs_dst}")

    if env_dst.exists() and not args.force:
        print(f".env already exists at {env_dst}. Use --force to overwrite.")
    else:
        shutil.copy(tmpl_dir / "env.example", env_dst)
        print(f"wrote {env_dst}")

    if args.interactive:
        print("\nQuick setup, press Enter to keep defaults or fill later:\n")
        import yaml
        prof = yaml.safe_load(profile_dst.read_text()) or {}
        prof["name"] = _prompt("Full name", prof.get("name", ""))
        prof["identity_line"] = _prompt(
            'One-line identity (e.g. "a Computer Science graduate from KNUST")',
            prof.get("identity_line", ""),
        )
        prof["portfolio"] = _prompt("Portfolio URL", prof.get("portfolio", ""))
        prof["cv_path"] = _prompt("Absolute path to CV pdf", prof.get("cv_path", ""))
        prof["transcript_path"] = _prompt("Absolute path to transcript pdf", prof.get("transcript_path", ""))
        prof["degree_status"] = _prompt("Highest degree (bachelors/masters)", prof.get("degree_status", "bachelors"))
        prof["target_term"] = _prompt("Target term", prof.get("target_term", "Fall 2027"))
        prof["target_degree"] = _prompt("Target degree (PhD/MSc)", prof.get("target_degree", "PhD"))
        prof["review_email"] = _prompt("Review inbox (where drafts land)", prof.get("review_email", ""))
        profile_dst.write_text(yaml.safe_dump(prof, sort_keys=False))
        print(f"\nupdated {profile_dst}")

    print("\nNext steps:")
    print(f"  1. Fill in secrets in {env_dst} (ANTHROPIC_API_KEY, SMTP_*)")
    print(f"  2. Edit {profile_dst} to add your seed_projects (3 to 10 flagships)")
    print(f"  3. Optional: edit {programs_dst} to add target programs")
    print(f"  4. Run: grad-agent sync           # scan projects")
    print(f"  5. Run: grad-agent run --dry-run  # preview one batch")
    print(f"  6. Run: grad-agent register-claude  # get MCP install command")
    return 0


def cmd_server(_: argparse.Namespace) -> int:
    from . import server as _server
    _server.mcp.run()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from . import daily_run
    res = daily_run.run_batch(n=args.n, area=args.area or None, dry_run=args.dry_run)
    print(res)
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    from . import catalog_sync
    src = args.source or "all"
    print(getattr(catalog_sync, f"sync_{src}", catalog_sync.sync_all)() if src != "all"
          else catalog_sync.sync_all())
    return 0


def _resolve_grad_agent_exe() -> str:
    """Return the command Claude Code should run to launch this install.
    Order of preference:
      1. `grad-agent` on PATH  (clean form, works after `pipx ensurepath`)
      2. sys.argv[0] if it looks like a grad-agent script  (matches how the
         user just invoked us)
      3. A `grad-agent` binary next to the current Python  (pipx layout)
      4. `<sys.executable> -m grad_agent.cli`  (universal fallback)
    """
    from pathlib import Path

    on_path = shutil.which("grad-agent")
    if on_path:
        return on_path

    argv0 = Path(sys.argv[0]) if sys.argv and sys.argv[0] else None
    if argv0 and argv0.is_absolute() and argv0.name.startswith("grad-agent"):
        return str(argv0)

    adj = Path(sys.executable).parent / "grad-agent"
    if adj.exists():
        return str(adj)

    return f"{sys.executable} -m grad_agent.cli"


def cmd_register_claude(_: argparse.Namespace) -> int:
    exe = _resolve_grad_agent_exe()
    on_path = shutil.which("grad-agent")
    cmd = f"claude mcp add grad-agent {exe} server"
    print("Run this once to register with Claude Code:\n")
    print(f"    {cmd}\n")
    if not on_path:
        print("Note: `grad-agent` is not on your PATH yet.")
        print("Run `pipx ensurepath` and open a new terminal to get the shorter form")
        print("`claude mcp add grad-agent grad-agent server`.\n")
    print("Then in a Claude Code session type /mcp to confirm it's connected.")
    return 0


def cmd_path(_: argparse.Namespace) -> int:
    print(config.home())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="grad-agent", description=__doc__)
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help="Interactive setup")
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--interactive", action="store_true", default=True)
    p_init.add_argument("--no-interactive", dest="interactive", action="store_false")
    p_init.set_defaults(func=cmd_init)

    p_server = sub.add_parser("server", help="Start MCP stdio server")
    p_server.set_defaults(func=cmd_server)

    p_run = sub.add_parser("run", help="Run today's outreach batch")
    p_run.add_argument("-n", type=int, default=3)
    p_run.add_argument("--area", default="")
    p_run.add_argument("--dry-run", action="store_true")
    p_run.set_defaults(func=cmd_run)

    p_sync = sub.add_parser("sync", help="Sync project catalog")
    p_sync.add_argument("--source", choices=["all", "github", "hf", "local"], default="all")
    p_sync.set_defaults(func=cmd_sync)

    p_reg = sub.add_parser("register-claude", help="Print the claude mcp add command")
    p_reg.set_defaults(func=cmd_register_claude)

    p_path = sub.add_parser("path", help="Print GRAD_AGENT_HOME")
    p_path.set_defaults(func=cmd_path)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(); return 1

    config.load_env_file()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
