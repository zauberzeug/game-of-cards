"""`goc install` — scaffold the methodology into a target repo.

Drops the shared deck/config scaffold plus selected agent harness assets into
the current working directory. The default harness remains Claude Code; Codex
uses the shared AGENTS.md guidance without Claude-only skills or hooks.
Idempotent — second runs detect existing installs via `deck/.goc-version` and
exit clean.

Reads templates via `importlib.resources` so it works from a wheel install.
"""

from __future__ import annotations

import re
import shutil
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import click

from goc import __version__

GOC_BEGIN = f"<!-- BEGIN GOC v{__version__} -->"
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\d.]+ -->")
GOC_END = "<!-- END GOC -->"

SUPPORTED_AGENTS = ("claude", "codex")
DEFAULT_AGENTS = ("claude",)

PRE_COMMIT_HOOK = """\
  - repo: local
    hooks:
      - id: goc-validate
        name: goc validate
        entry: goc validate
        language: system
        pass_filenames: false
        files: ^deck/.*$
"""


@dataclass(frozen=True)
class PlannedWrite:
    owner: str
    action: str
    path: Path


@dataclass(frozen=True)
class GuidanceBlock:
    path: str
    template: str
    header: str


AGENTS_GUIDANCE = GuidanceBlock("AGENTS.md", "AGENTS_GOC.md", "# Agent Guidelines")
CLAUDE_GUIDANCE = GuidanceBlock("CLAUDE.md", "CLAUDE_GOC.md", "# Claude Code Guidelines")


def _templates_root() -> Path:
    """Return the on-disk path to the bundled `goc/templates/` tree."""

    return Path(str(resources.files("goc.templates")))


def _parse_agents(agent_specs: tuple[str, ...]) -> tuple[str, ...]:
    """Parse comma-separated/repeated `--agents` values into known harness names."""

    tokens: list[str] = []
    for spec in agent_specs:
        tokens.extend(part.strip().lower() for part in spec.split(",") if part.strip())
    if not tokens:
        tokens = list(DEFAULT_AGENTS)

    unknown = sorted(set(tokens) - set(SUPPORTED_AGENTS))
    if unknown:
        supported = ", ".join(SUPPORTED_AGENTS)
        raise click.BadParameter(
            f"unknown agent(s): {', '.join(unknown)}; supported: {supported}",
            param_hint="--agents",
        )

    requested = set(tokens)
    return tuple(agent for agent in SUPPORTED_AGENTS if agent in requested)


def _detect_existing(deck_dir: Path) -> str | None:
    """Return the version pinned by `deck/.goc-version`, or None if absent."""

    sentinel = deck_dir / ".goc-version"
    if not sentinel.exists():
        return None
    return sentinel.read_text().strip()


def _plan_writes(target: Path, templates: Path, agents: tuple[str, ...]) -> list[PlannedWrite]:
    """Compute the list of writes the installer will perform."""

    writes: list[PlannedWrite] = []
    writes.append(PlannedWrite("shared", "write", target / "deck" / "log.md"))
    writes.append(PlannedWrite("shared", "write", target / "deck" / ".goc-version"))
    config_src = templates / "game_of_cards"
    for asset in config_src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(config_src)
        writes.append(PlannedWrite("shared", "write", target / ".game-of-cards" / rel))
    agents_owner = "codex" if "codex" in agents else "shared"
    writes.append(PlannedWrite(agents_owner, "append", target / AGENTS_GUIDANCE.path))
    if "claude" in agents:
        skills_src = templates / "skills"
        for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
            for asset in skill_dir.rglob("*"):
                if asset.is_dir() or "__pycache__" in asset.parts:
                    continue
                rel = asset.relative_to(skills_src)
                writes.append(PlannedWrite("claude", "write", target / ".claude" / "skills" / rel))
        writes.append(PlannedWrite("claude", "write", target / ".claude" / "hooks" / "user-prompt-submit-goc.py"))
        writes.append(PlannedWrite("claude", "append", target / CLAUDE_GUIDANCE.path))
    writes.append(PlannedWrite("shared", "append", target / ".pre-commit-config.yaml"))
    return writes


def _plan_upgrade_writes(target: Path, templates: Path, agents: tuple[str, ...]) -> list[PlannedWrite]:
    """Compute the list of writes the upgrader will perform."""

    writes: list[PlannedWrite] = []
    for write in _plan_writes(target, templates, agents):
        if write.path.name == "log.md":
            continue
        action = "sync" if write.action == "write" else write.action
        writes.append(PlannedWrite(write.owner, action, write.path))
    return writes


def _print_plan(command: str, target: Path, writes: list[PlannedWrite], agents: tuple[str, ...]) -> None:
    """Render a dry-run write plan with shared vs harness ownership."""

    click.echo(f"goc {command} (dry-run) — agents: {','.join(agents)} — {len(writes)} writes planned")
    for write in writes:
        click.echo(f"  {write.owner:6s} {write.action:6s} {write.path.relative_to(target)}")


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree, skipping `__pycache__`."""

    for asset in src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target)


def _append_marker_block(target: Path, block_body: str, *, header: str) -> None:
    """Append (or replace) a marker-bounded GoC section in a markdown file.

    Works for both AGENTS.md and CLAUDE.md — the marker pattern is identical;
    only the content and the file-creation header differ.
    """

    block = f"{GOC_BEGIN}\n{block_body.rstrip()}\n{GOC_END}\n"
    if not target.exists():
        target.write_text(f"{header}\n\n{block}")
        return
    text = target.read_text()
    pattern = re.compile(rf"{GOC_BEGIN_RE.pattern}.*?{re.escape(GOC_END)}\n?", re.DOTALL)
    if pattern.search(text):
        target.write_text(pattern.sub(block, text))
        return
    target.write_text(text.rstrip() + "\n\n" + block)


def _append_precommit_hook(target: Path) -> None:
    """Append the `goc validate` hook to `.pre-commit-config.yaml` (creating it)."""

    if not target.exists():
        target.write_text("repos:\n" + PRE_COMMIT_HOOK)
        return
    text = target.read_text()
    if "id: goc-validate" in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    target.write_text(text + PRE_COMMIT_HOOK)


def _sync_methodology_blocks(target: Path, templates: Path, agents: tuple[str, ...]) -> None:
    """Write the selected marker-bounded methodology blocks."""

    agents_body = (templates / AGENTS_GUIDANCE.template).read_text()
    _append_marker_block(target / AGENTS_GUIDANCE.path, agents_body, header=AGENTS_GUIDANCE.header)

    if "claude" in agents:
        claude_body = (templates / CLAUDE_GUIDANCE.template).read_text()
        _append_marker_block(target / CLAUDE_GUIDANCE.path, claude_body, header=CLAUDE_GUIDANCE.header)


def _sync_claude_harness(target: Path, templates: Path, *, replace_skills: bool = False) -> None:
    """Copy Claude-only skills and prompt hook."""

    skills_dst = target / ".claude" / "skills"
    if replace_skills and skills_dst.exists():
        shutil.rmtree(skills_dst)
    skills_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(templates / "skills", skills_dst)

    hooks_dst = target / ".claude" / "hooks"
    hooks_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(templates / "hooks" / "user-prompt-submit.py", hooks_dst / "user-prompt-submit-goc.py")


AGENTS_HELP = "Agent harnesses to install; repeat or comma-separate. Default: claude. Supported: claude, codex."


@click.command()
@click.option("--dry-run", is_flag=True, help="Print planned writes; do not touch the filesystem.")
@click.option("--agents", "agent_specs", multiple=True, help=AGENTS_HELP)
def install(dry_run: bool, agent_specs: tuple[str, ...]) -> None:
    """Scaffold a fresh repo with the shared GoC files and selected harnesses."""

    target = Path.cwd().resolve()
    deck_dir = target / "deck"
    templates = _templates_root()
    agents = _parse_agents(agent_specs)

    writes = _plan_writes(target, templates, agents)
    if dry_run:
        _print_plan("install", target, writes, agents)
        return

    existing = _detect_existing(deck_dir)
    if existing is not None:
        click.echo(f"already installed (deck/.goc-version → {existing})", err=True)
        click.echo("run `goc upgrade` to re-sync templates.")
        sys.exit(1)

    if "claude" in agents:
        _sync_claude_harness(target, templates)

    deck_dir.mkdir(parents=True, exist_ok=True)
    (deck_dir / "log.md").write_text("# Deck Log\n\nAppend deck-level events here (sprint notes, schema bumps, etc.).\n")
    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    config_src = templates / "game_of_cards"
    config_dst = target / ".game-of-cards"
    config_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(config_src, config_dst)

    _sync_methodology_blocks(target, templates, agents)

    _append_precommit_hook(target / ".pre-commit-config.yaml")

    click.echo(f"goc {__version__} installed for agents: {','.join(agents)}.")
    click.echo("Next: `goc new my-first-card`. Run `goc upgrade` later to sync template updates.")


@click.command()
@click.option("--dry-run", is_flag=True, help="Print planned writes; do not touch the filesystem.")
@click.option("--agents", "agent_specs", multiple=True, help=AGENTS_HELP)
def upgrade(dry_run: bool, agent_specs: tuple[str, ...]) -> None:
    """Re-sync skill templates, AGENTS.md, and CLAUDE.md sections from the installed package version."""

    target = Path.cwd().resolve()
    deck_dir = target / "deck"
    templates = _templates_root()
    agents = _parse_agents(agent_specs)
    agents_explicit = bool(agent_specs)

    existing = _detect_existing(deck_dir)
    if existing is None:
        click.echo("no existing install detected — run `goc install` first.", err=True)
        sys.exit(1)

    if existing == __version__ and not dry_run and not agents_explicit:
        click.echo(f"already at goc {__version__} — nothing to do.")
        return

    if dry_run:
        click.echo(f"goc upgrade would sync {existing} → {__version__}")
        _print_plan("upgrade", target, _plan_upgrade_writes(target, templates, agents), agents)
        return

    if "claude" in agents:
        _sync_claude_harness(target, templates, replace_skills=True)

    config_dst = target / ".game-of-cards"
    if config_dst.exists():
        shutil.rmtree(config_dst)
    config_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(templates / "game_of_cards", config_dst)

    _sync_methodology_blocks(target, templates, agents)

    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    click.echo(f"goc upgrade complete for agents: {','.join(agents)} — {existing} → {__version__}.")


if __name__ == "__main__":
    install()
