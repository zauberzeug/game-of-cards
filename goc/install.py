"""`goc install` — scaffold the methodology into a target repo.

Drops the methodology assets (skills, hook, CLAUDE.md sections, pre-commit
hook, deck scaffold) into the current working directory. Idempotent — second
runs detect existing installs via `deck/.goc-version` and exit clean.

Reads templates via `importlib.resources` so it works from a wheel install.
"""

from __future__ import annotations

import re
import shutil
import sys
from importlib import resources
from pathlib import Path

import click

from goc import __version__

# Marker bracket lets `goc upgrade` re-sync without clobbering user content.
GOC_BEGIN = f"<!-- BEGIN GOC v{__version__} -->"
GOC_BEGIN_RE = re.compile(r"<!-- BEGIN GOC v[\d.]+ -->")
GOC_END = "<!-- END GOC -->"

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


def _templates_root() -> Path:
    """Return the on-disk path to the bundled `goc/templates/` tree."""

    return Path(str(resources.files("goc.templates")))


def _detect_existing(deck_dir: Path) -> str | None:
    """Return the version pinned by `deck/.goc-version`, or None if absent."""

    sentinel = deck_dir / ".goc-version"
    if not sentinel.exists():
        return None
    return sentinel.read_text().strip()


def _plan_writes(target: Path, templates: Path) -> list[tuple[str, Path]]:
    """Compute the list of writes the installer will perform.

    Returns (action, destination_path) tuples for `--dry-run` printing and
    smoke-test enumeration.
    """

    writes: list[tuple[str, Path]] = []
    skills_src = templates / "skills"
    for skill_dir in sorted(p for p in skills_src.iterdir() if p.is_dir()):
        for asset in skill_dir.rglob("*"):
            if asset.is_dir() or "__pycache__" in asset.parts:
                continue
            rel = asset.relative_to(skills_src)
            writes.append(("write", target / ".claude" / "skills" / rel))
    writes.append(("write", target / ".claude" / "hooks" / "user-prompt-submit-goc.py"))
    writes.append(("write", target / "deck" / "log.md"))
    writes.append(("write", target / "deck" / ".goc-version"))
    config_src = templates / "game_of_cards"
    for asset in config_src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(config_src)
        writes.append(("write", target / ".game-of-cards" / rel))
    writes.append(("append", target / "CLAUDE.md"))
    writes.append(("append", target / ".pre-commit-config.yaml"))
    return writes


def _copy_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree, skipping `__pycache__`."""

    for asset in src.rglob("*"):
        if asset.is_dir() or "__pycache__" in asset.parts:
            continue
        rel = asset.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, target)


def _append_claude_md_block(target: Path, block_body: str) -> None:
    """Append (or replace) the marker-bounded GoC section in CLAUDE.md."""

    block = f"{GOC_BEGIN}\n{block_body.rstrip()}\n{GOC_END}\n"
    if not target.exists():
        target.write_text(f"# AI Agent Guidelines\n\n{block}")
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


@click.command()
@click.option("--dry-run", is_flag=True, help="Print planned writes; do not touch the filesystem.")
def install(dry_run: bool) -> None:
    """Scaffold a fresh repo with goc skills, deck, and config stubs."""

    target = Path.cwd().resolve()
    deck_dir = target / "deck"
    templates = _templates_root()

    existing = _detect_existing(deck_dir)
    if existing is not None:
        click.echo(f"already installed (deck/.goc-version → {existing})", err=True)
        click.echo("run `goc upgrade` to re-sync templates.")
        sys.exit(1)

    writes = _plan_writes(target, templates)
    if dry_run:
        click.echo(f"goc install (dry-run) — {len(writes)} writes planned")
        for action, path in writes:
            click.echo(f"  {action:6s} {path.relative_to(target)}")
        return

    skills_dst = target / ".claude" / "skills"
    skills_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(templates / "skills", skills_dst)

    hooks_dst = target / ".claude" / "hooks"
    hooks_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(templates / "hooks" / "user-prompt-submit.py", hooks_dst / "user-prompt-submit-goc.py")

    deck_dir.mkdir(parents=True, exist_ok=True)
    (deck_dir / "log.md").write_text("# Deck Log\n\nAppend deck-level events here (sprint notes, schema bumps, etc.).\n")
    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    config_src = templates / "game_of_cards"
    config_dst = target / ".game-of-cards"
    config_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(config_src, config_dst)

    block_body = (templates / "CLAUDE_GOC.md").read_text()
    _append_claude_md_block(target / "CLAUDE.md", block_body)

    _append_precommit_hook(target / ".pre-commit-config.yaml")

    click.echo(f"goc {__version__} installed.")
    click.echo("Next: `goc new my-first-card`. Run `goc upgrade` later to sync template updates.")


@click.command()
@click.option("--dry-run", is_flag=True, help="Print planned writes; do not touch the filesystem.")
def upgrade(dry_run: bool) -> None:
    """Re-sync skill templates and CLAUDE.md sections from the installed package version."""

    target = Path.cwd().resolve()
    deck_dir = target / "deck"
    templates = _templates_root()

    existing = _detect_existing(deck_dir)
    if existing is None:
        click.echo("no existing install detected — run `goc install` first.", err=True)
        sys.exit(1)

    if existing == __version__ and not dry_run:
        click.echo(f"already at goc {__version__} — nothing to do.")
        return

    if dry_run:
        click.echo(f"goc upgrade (dry-run) — {existing} → {__version__}")
        click.echo("  re-extract .claude/skills/ from package")
        click.echo("  re-extract .game-of-cards/ from package")
        click.echo("  re-sync CLAUDE.md GOC block")
        click.echo("  bump deck/.goc-version")
        return

    skills_dst = target / ".claude" / "skills"
    if skills_dst.exists():
        shutil.rmtree(skills_dst)
    skills_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(templates / "skills", skills_dst)

    config_dst = target / ".game-of-cards"
    if config_dst.exists():
        shutil.rmtree(config_dst)
    config_dst.mkdir(parents=True, exist_ok=True)
    _copy_tree(templates / "game_of_cards", config_dst)

    block_body = (templates / "CLAUDE_GOC.md").read_text()
    _append_claude_md_block(target / "CLAUDE.md", block_body)

    (deck_dir / ".goc-version").write_text(__version__ + "\n")

    click.echo(f"goc upgrade complete — {existing} → {__version__}.")


if __name__ == "__main__":
    install()
