#!/usr/bin/env python3
"""One-off port script: goc/templates/skills/<name>/SKILL.md → openclaw-plugin/skills/<name>/SKILL.md.

Performs mechanical Claude-→-host-neutral transformations:
  - `Skill(name)` → "the `name` skill"
  - `Bash tool` → "shell" / "goc tool" contextually
  - Drops the `## Preflight` block (Claude-specific block-execution check).
    OpenClaw registers the goc tool programmatically; preflight is moot.
  - Drops the `## Context` section's `!` block embedded execution
    (Claude Code's pre-fetch syntax). Replaces with a note that the
    agent can call the goc tool to obtain that context.
  - Removes Claude-specific `argument-hint` / `$ARGUMENTS` references.

The port is deterministic: re-running it must reproduce the committed
`openclaw-plugin/skills/` byte-for-byte. `--check` asserts exactly that
(a fresh re-port equals what is committed). The same comparison is the
CI drift guard — `tests/test_plugin_mirror_parity.py` calls
`drifted_skills()` from the regression-test suite (the bot's GITHUB_TOKEN
cannot edit `.github/workflows/`, so the guard lives in a test rather
than a workflow step). A template edit that is not propagated by a
re-port turns the build red instead of rotting silently.

Usage:
    python scripts/port_skills_to_openclaw.py          # re-port + write
    python scripts/port_skills_to_openclaw.py --check   # dry-run, exit 1 on drift
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "goc" / "templates" / "skills"
DST_DIR = ROOT / "openclaw-plugin" / "skills"

# Host-specific complement skills — every supported agent that GoC ships a
# harness for. Skills with one of these prefixes are agent-specific and never
# port to OpenClaw (they belong to the named host's plugin/install instead).
# `openclaw-` is intentionally absent: openclaw-prefixed skills (e.g.
# `openclaw-kickoff`) are the OpenClaw host complement and DO get ported.
HOST_PREFIXES = ("claude-", "codex-")

# Order matters: more specific patterns first.
SUBSTITUTIONS: list[tuple[re.Pattern[str], str]] = [
    # Skill(name) WITH ARGS inside backticks — `Skill(advance-card) <title> active`
    # collapses to "the `advance-card` skill (with `<title> active`)" instead
    # of the nested-backtick mess produced by the simpler patterns below.
    (re.compile(r"`Skill\(([a-z-]+)\)\s+([^`]+)`"),
     r"the `\1` skill (with `\2`)"),
    # Bare `Skill(name)` inside backticks.
    (re.compile(r"`Skill\(([a-z-]+)\)`"), r"the `\1` skill"),
    # Standalone Skill(name) — letters and hyphens only.
    (re.compile(r"Skill\(([a-z-]+)\)"), r"the `\1` skill"),
    # Skill(<placeholder | placeholder>) — meta-syntax describing a choice
    # of skills, used in recommendations / examples.
    (re.compile(r"Skill\(<([^>]+)>\)"), r"the `<\1>` skill"),
    # Bash tool → host-neutral.
    (re.compile(r"\bBash tool\b"), "shell"),
    # Claude Code references — drop or rephrase.
    (re.compile(r"\bClaude Code\b"), "the host"),
    # Standalone Claude (NOT followed by " Code" — that's caught above).
    # These genericize references to the agent runtime ("Claude runs the
    # card pipeline" → "the agent runs the card pipeline").
    (re.compile(r"\bClaude\b(?! Code)"), "the agent"),
    # Argument-hint / $ARGUMENTS — Claude-specific slash-command syntax.
    (re.compile(r"^argument-hint:.*$\n", re.MULTILINE), ""),
    (re.compile(r"User argument: \$ARGUMENTS — "), "Optional argument — "),
    (re.compile(r"\$ARGUMENTS"), "the user's argument"),
]


PREFLIGHT_RE = re.compile(
    r"## Preflight\n\n.*?(?=\n## |\n# |\Z)", re.DOTALL,
)

# Replace `!`backtick blocks (Claude Code's pre-execute) inside ## Context with
# a guidance paragraph. The block is `!` followed by a backticked command on
# the same logical line (or ! on its own line followed by a command in
# fenced code).
CONTEXT_BLOCK_RE = re.compile(
    r"## Context\n\n((?:!`[^`]+`\n\n?)+)",
    re.MULTILINE,
)


def transform_context_block(match: re.Match[str]) -> str:
    """Replace the embedded-execution context with a host-neutral note."""
    raw = match.group(1)
    commands = re.findall(r"!`([^`]+)`", raw)
    bullet = "\n".join(f"- `{cmd}`" for cmd in commands)
    return (
        "## Context\n\n"
        "Before running the body of this skill, the agent should see current "
        "deck state. Run these via the `goc` tool (top-level filters like "
        "`--status` / `--tag` / `--worker` map to the tool's `flags` "
        "parameter; the subcommand maps to `verb`). For bare-queue listings "
        "with no subcommand, shell out via the `exec` tool:\n\n"
        f"{bullet}\n\n"
    )


# Inline `!`backtick`` blocks scattered through the body (outside ## Context).
# Claude Code pre-executes these and embeds the output; OpenClaw has no
# equivalent. Convert to a plain backticked example so the skill body still
# reads as a recipe.
INLINE_BANG_BLOCK_RE = re.compile(r"^!`([^`]+)`", re.MULTILINE)


def render_skill(src: Path) -> str:
    """Return the host-neutral port of a source skill (pure — no I/O)."""
    text = src.read_text(encoding="utf-8")

    # Drop the `## Preflight` block entirely.
    text = PREFLIGHT_RE.sub("", text, count=1)

    # Replace `## Context` embedded-execution with a host-neutral note.
    text = CONTEXT_BLOCK_RE.sub(transform_context_block, text)

    # Strip the `!` prefix from any remaining inline backtick blocks.
    text = INLINE_BANG_BLOCK_RE.sub(r"`\1`", text)

    # Apply the small substitutions.
    for pattern, repl in SUBSTITUTIONS:
        text = pattern.sub(repl, text)

    # Collapse triple+ blank lines down to double.
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Trim leading whitespace immediately after frontmatter so we don't get
    # an unsightly blank line gap from the dropped Preflight section.
    text = re.sub(r"(^---\n.*?\n---\n)\n+", r"\1\n", text, count=1, flags=re.DOTALL)

    return text


def port_skill(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(render_skill(src), encoding="utf-8")


def _portable_skill_dirs() -> list[Path]:
    """Source skill dirs that port to OpenClaw (host-specific complements excluded)."""
    dirs = []
    for skill_dir in sorted(SRC_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if any(skill_dir.name.startswith(prefix) for prefix in HOST_PREFIXES):
            continue
        if (skill_dir / "SKILL.md").is_file():
            dirs.append(skill_dir)
    return dirs


def _expected_dst_names() -> set[str]:
    """Names of skill dirs that should exist under DST_DIR — one per portable source.

    The single source of truth for "what belongs in the OpenClaw payload",
    reused by both the drift check and the prune so they cannot diverge.
    """
    return {skill_dir.name for skill_dir in _portable_skill_dirs()}


def _orphaned_ported_dirs(expected: set[str] | None = None) -> list[Path]:
    """Ported skill dirs under DST_DIR with no portable-source counterpart.

    Mirrors the dst-only handling in scripts/sync_plugin_assets.py: a dst
    skill dir whose name has no source is stale (the source was renamed or
    removed) and must be pruned. Host-specific complement dirs (claude-/codex-
    prefixed) are never managed by this porter, so they are left untouched
    rather than flagged or deleted.
    """
    if not DST_DIR.is_dir():
        return []
    if expected is None:
        expected = _expected_dst_names()
    orphans: list[Path] = []
    for child in sorted(DST_DIR.iterdir()):
        if not child.is_dir() or child.name in expected:
            continue
        if any(child.name.startswith(prefix) for prefix in HOST_PREFIXES):
            continue
        if (child / "SKILL.md").is_file():
            orphans.append(child)
    return orphans


def drifted_skills() -> list[Path]:
    """Committed ported skills whose content differs from a fresh re-port.

    A non-empty result means a template was edited without re-running the
    porter (or a ported file was hand-edited), OR a ported skill dir has lost
    its source (an orphan). The list is the set of dst paths a re-port would
    rewrite or remove. Reused by the porter's own `--check` and by the CI
    regression test so both read the same definition of drift.
    """
    expected = _expected_dst_names()
    drifted: list[Path] = []
    for skill_dir in _portable_skill_dirs():
        dst = DST_DIR / skill_dir.name / "SKILL.md"
        rendered = render_skill(skill_dir / "SKILL.md")
        actual = dst.read_text(encoding="utf-8") if dst.is_file() else None
        if actual != rendered:
            drifted.append(dst)
    drifted.extend(orphan / "SKILL.md" for orphan in _orphaned_ported_dirs(expected))
    return drifted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report ported skills that drift from a fresh re-port and exit 1 "
             "without modifying anything (CI mode).",
    )
    args = parser.parse_args(argv)

    if not SRC_DIR.is_dir():
        print(f"ERROR: source skills dir not found: {SRC_DIR}", file=sys.stderr)
        return 1

    if args.check:
        drifted = drifted_skills()
        if drifted:
            print("ERROR: openclaw-plugin/skills/ have drifted from goc/templates/skills/:")
            for p in drifted:
                print(f"  {p.relative_to(ROOT)}")
            print("Fix: run `python scripts/port_skills_to_openclaw.py` and commit the result.")
            return 1
        print("OK — openclaw-plugin/skills/ match a fresh port of goc/templates/skills/.")
        return 0

    DST_DIR.mkdir(parents=True, exist_ok=True)
    expected = _expected_dst_names()
    ported = 0
    for skill_dir in _portable_skill_dirs():
        port_skill(skill_dir / "SKILL.md", DST_DIR / skill_dir.name / "SKILL.md")
        ported += 1

    # Prune orphaned ported skill dirs (source renamed or removed) so a stale
    # skill can't ship to OpenClaw consumers undetected.
    orphans = _orphaned_ported_dirs(expected)
    for orphan in orphans:
        shutil.rmtree(orphan)

    skipped = [
        d.name for d in sorted(SRC_DIR.iterdir())
        if d.is_dir() and any(d.name.startswith(p) for p in HOST_PREFIXES)
    ]
    print(f"ported {ported} skills to {DST_DIR.relative_to(ROOT)}")
    if orphans:
        print(f"pruned {len(orphans)} orphaned ported skill dir(s): {', '.join(o.name for o in orphans)}")
    if skipped:
        print(f"skipped (host-specific complements): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
