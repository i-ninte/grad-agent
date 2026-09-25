"""grad-agent CLI.

Subcommands:
  init            Interactive setup: writes ~/.grad-agent/profile.yaml + .env
  server          Start the MCP stdio server (for `claude mcp add`).
  run             Run today's outreach batch and email the review inbox.
  sync            Sync catalog from GitHub + HuggingFace + local projects_dir.
  register-claude Print the `claude mcp add` command tailored to this install.
  install-skills  Link bundled skills into ~/.claude/skills/ (Claude Code).
  path            Print resolved GRAD_AGENT_HOME.
"""
from __future__ import annotations
import argparse
import os
import shutil
import sys
from pathlib import Path

from . import config


def _bundled_skills_dir() -> Path:
    pkg = Path(__file__).parent / "skills"
    if pkg.exists():
        return pkg
    return pkg.parent.parent / "skills"


def install_skills(target_dir: Path | None = None, force: bool = False, quiet: bool = False) -> list[str]:
    """Symlink each bundled skill into `target_dir` (default `~/.claude/skills/`).

    Falls back to copytree on filesystems where symlink is unavailable
    (e.g. Windows without developer mode). Existing symlinks to the
    bundled path are refreshed; existing real directories are left alone
    unless `force=True`.

    Returns the list of skill names that were installed or refreshed.
    """
    src = _bundled_skills_dir()
    if not src.exists():
        return []
    target = target_dir or (Path.home() / ".claude" / "skills")
    target.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    for skill_dir in sorted(p for p in src.iterdir() if p.is_dir()):
        dst = target / skill_dir.name
        try:
            if dst.is_symlink():
                dst.unlink()
            elif dst.exists():
                if not force:
                    if not quiet:
                        print(f"skip: {dst} already exists (use --force to overwrite)")
                    continue
                if dst.is_dir():
                    shutil.rmtree(dst)
                else:
                    dst.unlink()
            try:
                os.symlink(skill_dir, dst, target_is_directory=True)
            except (OSError, NotImplementedError):
                shutil.copytree(skill_dir, dst)
            installed.append(skill_dir.name)
            if not quiet:
                print(f"installed skill: {dst} -> {skill_dir}")
        except Exception as e:
            if not quiet:
                print(f"warn: could not install {skill_dir.name}: {e}", file=sys.stderr)
    return installed


def cmd_install_skills(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser() if args.target else None
    installed = install_skills(target_dir=target, force=args.force)
    if not installed:
        print("No skills were installed.")
        return 1
    print(f"\nDone. Restart Claude Code / Claude Desktop to pick up: {', '.join(installed)}")
    return 0


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    v = input(f"{label}{suffix}: ").strip()
    return v or default


def _update_env_var(env_path: Path, key: str, value: str) -> None:
    """Set KEY=VALUE in a dotenv file, preserving order and other lines.

    Replaces the existing (commented or uncommented) line for `key`, or
    appends `KEY=VALUE` at the end if no line exists. Empty `value`
    removes the setting by commenting it out. Idempotent.
    """
    env_path.parent.mkdir(parents=True, exist_ok=True)
    lines = env_path.read_text().splitlines() if env_path.exists() else []
    new_line = f"{key}={value}" if value else f"# {key}="
    hit = False
    out = []
    import re
    pat = re.compile(rf"^\s*#?\s*{re.escape(key)}\s*=")
    for ln in lines:
        if pat.match(ln) and not hit:
            out.append(new_line)
            hit = True
        else:
            out.append(ln)
    if not hit:
        out.append(new_line)
    env_path.write_text("\n".join(out) + "\n")


def cmd_set_letterhead(args: argparse.Namespace) -> int:
    env_dst = config.env_path()
    if not env_dst.exists():
        print(f"error: {env_dst} not found. Run `grad-agent init` first.", file=sys.stderr)
        return 1
    path_val = args.path.strip() if args.path else ""
    if path_val:
        p = Path(path_val).expanduser()
        if not p.exists():
            print(f"warn: {p} does not exist yet (saving the path anyway)", file=sys.stderr)
        path_val = str(p)
    _update_env_var(env_dst, "LOR_LETTERHEAD_PATH", path_val)
    if args.width:
        _update_env_var(env_dst, "LOR_LETTERHEAD_WIDTH", args.width.strip())
    if path_val:
        print(f"LOR_LETTERHEAD_PATH set to {path_val}")
    else:
        print("LOR_LETTERHEAD_PATH cleared (plain top block on next compile)")
    if args.width:
        print(f"LOR_LETTERHEAD_WIDTH set to {args.width}")
    return 0


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

    scholarships_dst = home / "scholarships.yaml"
    if not scholarships_dst.exists() or args.force:
        shutil.copy(tmpl_dir / "scholarships.example.yaml", scholarships_dst)
        print(f"wrote {scholarships_dst}")

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

        lh_path = _prompt(
            "Path to letterhead/logo image for LOR compile (png/jpg/pdf, blank to skip)",
            "",
        )
        if lh_path:
            lh_expanded = str(Path(lh_path).expanduser())
            if not Path(lh_expanded).exists():
                print(f"  warn: {lh_expanded} does not exist yet (saving the path anyway)")
            _update_env_var(env_dst, "LOR_LETTERHEAD_PATH", lh_expanded)
            lh_width = _prompt("Letterhead width (LaTeX length)", "2.2in")
            _update_env_var(env_dst, "LOR_LETTERHEAD_WIDTH", lh_width)
            print(f"updated {env_dst} with LOR_LETTERHEAD_PATH / LOR_LETTERHEAD_WIDTH")

    try:
        installed = install_skills(quiet=True)
        if installed:
            print(f"linked skills into ~/.claude/skills/: {', '.join(installed)}")
    except Exception as e:
        print(f"warn: skill auto-install skipped: {e}", file=sys.stderr)

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


def cmd_schedule(args: argparse.Namespace) -> int:
    """Emit the OS-appropriate daily-schedule template and install instructions."""
    import platform
    from pathlib import Path
    tmpl_dir = config.TEMPLATES
    system = platform.system()

    if args.dest:
        dest = Path(args.dest).expanduser().resolve()
    else:
        dest = Path.cwd()
    dest.mkdir(parents=True, exist_ok=True)

    if system == "Darwin":
        src = tmpl_dir / "com.gradagent.daily.plist"
        out = dest / src.name
        out.write_text(src.read_text())
        print(f"wrote {out}\n")
        print("Install:")
        print(f"  cp {out} ~/Library/LaunchAgents/")
        print(f"  launchctl load ~/Library/LaunchAgents/{src.name}")
        return 0

    if system == "Windows":
        src = tmpl_dir / "grad-agent-daily.xml"
        out = dest / src.name
        # Task Scheduler wants UTF-16 XML; the template is already the correct shape.
        out.write_bytes(src.read_bytes())
        print(f"wrote {out}\n")
        print("Install (run in an elevated PowerShell):")
        print(f'  schtasks /Create /TN "grad-agent-daily" /XML "{out}"')
        print("Or via the Task Scheduler UI: Action, Import Task, select the XML.")
        return 0

    # Linux (and other POSIX)
    for name in ("grad-agent-daily.service", "grad-agent-daily.timer"):
        src = tmpl_dir / name
        out = dest / name
        out.write_text(src.read_text())
        print(f"wrote {out}")
    print("\nInstall:")
    print("  mkdir -p ~/.config/systemd/user")
    print(f"  cp {dest}/grad-agent-daily.* ~/.config/systemd/user/")
    print("  systemctl --user daemon-reload")
    print("  systemctl --user enable --now grad-agent-daily.timer")
    return 0


def cmd_cache(args: argparse.Namespace) -> int:
    from .sources import semantic_scholar as s2
    if args.cache_cmd == "clear":
        if not args.query and not args.all:
            print("Give --query NAME to clear matching entries, or --all.")
            return 1
        n = s2.cache_invalidate(args.query or "", everything=args.all)
        print(f"removed {n} cache entr{'y' if n == 1 else 'ies'}")
        return 0
    print("unknown cache subcommand")
    return 1


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

    p_skills = sub.add_parser(
        "install-skills",
        help="Symlink bundled skills (lor-writing, sop-writing) into ~/.claude/skills/",
    )
    p_skills.add_argument("--target", default="",
                          help="Override target dir (default: ~/.claude/skills)")
    p_skills.add_argument("--force", action="store_true",
                          help="Replace existing non-symlink entries with the same name")
    p_skills.set_defaults(func=cmd_install_skills)

    p_lh = sub.add_parser(
        "set-letterhead",
        help="Write LOR_LETTERHEAD_PATH into ~/.grad-agent/.env (blank path clears it)",
    )
    p_lh.add_argument("path", nargs="?", default="",
                      help="Absolute path to letterhead image (png/jpg/pdf). Omit or empty to clear.")
    p_lh.add_argument("--width", default="",
                      help="LaTeX length for the letterhead width, e.g. 2.5in (optional)")
    p_lh.set_defaults(func=cmd_set_letterhead)

    p_sched = sub.add_parser("schedule",
                             help="Emit the OS-appropriate daily-schedule template "
                                  "(launchd on macOS, Task Scheduler XML on Windows, "
                                  "systemd user timer on Linux)")
    p_sched.add_argument("--dest", default="",
                         help="Directory to write templates to (defaults to CWD)")
    p_sched.set_defaults(func=cmd_schedule)

    p_cache = sub.add_parser("cache", help="Manage the Semantic Scholar cache")
    p_cache.add_argument("cache_cmd", choices=["clear"])
    p_cache.add_argument("--query", default="", help="substring of author name or id")
    p_cache.add_argument("--all", action="store_true", help="wipe the whole cache")
    p_cache.set_defaults(func=cmd_cache)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(); return 1

    config.load_env_file()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
