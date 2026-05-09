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

NOT a daily sync — this is run once during the OpenClaw plugin scaffold
to seed `openclaw-plugin/skills/`. Subsequent edits to either side
(Claude or OpenClaw) are independent. The script is committed for
reproducibility and to make the diff inspectable.

Usage:
    python scripts/port_skills_to_openclaw.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "goc" / "templates" / "skills"
DST_DIR = ROOT / "openclaw-plugin" / "skills"

# Skills to skip (need separate authoring per `split-claude-specific-content...` card).
SKIP = frozenset({"kickoff"})

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


def port_skill(src: Path, dst: Path) -> None:
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

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"ERROR: source skills dir not found: {SRC_DIR}", file=sys.stderr)
        return 1

    DST_DIR.mkdir(parents=True, exist_ok=True)
    ported = 0
    skipped: list[str] = []
    for skill_dir in sorted(SRC_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        if skill_dir.name in SKIP:
            skipped.append(skill_dir.name)
            continue
        src = skill_dir / "SKILL.md"
        if not src.is_file():
            continue
        dst = DST_DIR / skill_dir.name / "SKILL.md"
        port_skill(src, dst)
        ported += 1

    print(f"ported {ported} skills to {DST_DIR.relative_to(ROOT)}")
    if skipped:
        print(f"skipped (Claude-specific, see split-claude-... card): {', '.join(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
