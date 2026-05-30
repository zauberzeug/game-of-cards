#!/usr/bin/env python3
"""Reproduce the OpenClaw skill porter's parenthetical-header miss.

Compiles `CONTEXT_BLOCK_RE` exactly as it lives in
`scripts/port_skills_to_openclaw.py` today and runs it against every
source skill under `goc/templates/skills/` that contains a `## Context`
heading. Exits 0 only when every such skill matches the regex — i.e.,
the bug is fixed. Today, two of five skills miss (`audit-deck`,
`refine-deck`), and the script exits 1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()

# Mirror of `scripts/port_skills_to_openclaw.py:84-87` verbatim.
CONTEXT_BLOCK_RE = re.compile(
    r"## Context\n\n((?:!`[^`]+`\n\n?)+)",
    re.MULTILINE,
)

# The matcher tracks the *intent* of the porter: any source skill that
# has a `## Context` heading followed by Claude's `!`backtick`` blocks
# is supposed to be rewritten. The regex above is the IS; the loose
# variant below is the SHOULD.
LOOSE_RE = re.compile(
    r"^## Context\b[^\n]*\n\n((?:!`[^`]+`\n\n?)+)",
    re.MULTILINE,
)


def main() -> int:
    skills_dir = REPO / "goc" / "templates" / "skills"
    rows: list[tuple[str, bool, bool]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        if "## Context" not in text:
            continue
        is_match = bool(CONTEXT_BLOCK_RE.search(text))
        should_match = bool(LOOSE_RE.search(text))
        rows.append((skill_md.parent.name, is_match, should_match))

    print(f"{'Skill':<16} {'REGEX MATCH':<14} {'EXPECTED'}")
    misses: list[str] = []
    for name, is_match, should_match in rows:
        is_label = "MATCH" if is_match else "MISS"
        should_label = "MATCH" if should_match else "MISS"
        print(f"{name:<16} {is_label:<14} {should_label}")
        if should_match and not is_match:
            misses.append(name)

    print()
    if misses:
        print(
            f"Misses: {len(misses)} of {len(rows)} — porter silently "
            f"skipped {', '.join(misses)}."
        )
        return 1
    print(f"No misses: {len(rows)} of {len(rows)} skills match. Bug is fixed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
