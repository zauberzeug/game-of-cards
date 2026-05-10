"""Console-script entry point for the `goc` command.

Builds the argparse parser from engine.py, adds `install` and `upgrade`
subcommands from install.py, and wires up the `--version` flag.
Registered as `goc = "goc.cli:main"` in pyproject.toml.
"""

from __future__ import annotations

import sys

from goc import __version__
from goc.engine import _build_parser, cli as engine_cli
from goc.install import (
    BRIEFING_TARGET_HELP,
    BRIEFING_TARGETS,
    INSTALL_AGENTS_HELP,
    KEEP_LOCAL_SKILLS_HELP,
    LOCAL_SKILLS_HELP,
    UPGRADE_AGENTS_HELP,
    install as _install,
    upgrade as _upgrade,
)


def main() -> None:
    """Console-script entry point."""
    argv = sys.argv[1:]

    # --version / -V before any other parsing
    if argv and argv[0] in ("-V", "--version"):
        print(f"goc, version {__version__}")
        return

    # Route install / upgrade to their argparse-independent functions
    if argv and argv[0] in ("install", "upgrade"):
        sub = argv[0]
        rest = argv[1:]
        import argparse

        if sub == "install":
            p = argparse.ArgumentParser(prog="goc install",
                description="Scaffold a fresh repo with the shared GoC files and selected harnesses.")
            p.add_argument("--dry-run", action="store_true",
                help="Print planned writes; do not touch the filesystem.")
            p.add_argument("--agents", dest="agent_specs", action="append", default=[],
                metavar="AGENTS", help=INSTALL_AGENTS_HELP)
            p.add_argument("--claude", dest="claude_flag", action="store_true",
                help="Shortcut for --agents claude.")
            p.add_argument("--codex", dest="codex_flag", action="store_true",
                help="Shortcut for --agents codex.")
            p.add_argument("--local-skills", dest="local_skills", action="store_true",
                help=LOCAL_SKILLS_HELP)
            p.add_argument("--briefing-target", dest="briefing_target", default="AGENTS.md",
                choices=list(BRIEFING_TARGETS), help=BRIEFING_TARGET_HELP)
            args = p.parse_args(rest)
            _install(
                dry_run=args.dry_run,
                agent_specs=tuple(args.agent_specs),
                claude_flag=args.claude_flag,
                codex_flag=args.codex_flag,
                local_skills=args.local_skills,
                briefing_target=args.briefing_target,
            )
        else:
            p = argparse.ArgumentParser(prog="goc upgrade",
                description="Re-sync skill templates, AGENTS.md, and CLAUDE.md sections from the installed package version.")
            p.add_argument("--dry-run", action="store_true",
                help="Print planned writes; do not touch the filesystem.")
            p.add_argument("--agents", dest="agent_specs", action="append", default=[],
                metavar="AGENTS", help=UPGRADE_AGENTS_HELP)
            p.add_argument("--claude", dest="claude_flag", action="store_true",
                help="Shortcut for --agents claude.")
            p.add_argument("--codex", dest="codex_flag", action="store_true",
                help="Shortcut for --agents codex.")
            p.add_argument("--keep-local-skills", dest="keep_local_skills", action="store_true",
                help=KEEP_LOCAL_SKILLS_HELP)
            p.add_argument("--briefing-target", dest="briefing_target", default=None,
                choices=list(BRIEFING_TARGETS), help=BRIEFING_TARGET_HELP)
            args = p.parse_args(rest)
            _upgrade(
                dry_run=args.dry_run,
                agent_specs=tuple(args.agent_specs),
                claude_flag=args.claude_flag,
                codex_flag=args.codex_flag,
                keep_local_skills=args.keep_local_skills,
                briefing_target=args.briefing_target,
            )
        return

    # Everything else goes to the argparse engine
    engine_cli(argv)


if __name__ == "__main__":
    main()
