#!/usr/bin/env python3
"""Reproduce the OpenClaw skill porter's parenthetical-header miss.

Imports `CONTEXT_BLOCK_RE` from `scripts/port_skills_to_openclaw.py` and
runs it against every source skill under `goc/templates/skills/` that
contains a `## Context` heading. Exits 0 only when every such skill
matches the regex — i.e., the bug is fixed. Before the fix, two of
five skills miss (`audit-deck`, `refine-deck`), and the script exits 1.
"""

from __future__ import annotations

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
sys.path.insert(0, str(REPO / "scripts"))

from port_skills_to_openclaw import CONTEXT_BLOCK_RE  # noqa: E402


def main() -> int:
    skills_dir = REPO / "goc" / "templates" / "skills"
    rows: list[tuple[str, bool]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        if "## Context" not in text:
            continue
        is_match = bool(CONTEXT_BLOCK_RE.search(text))
        rows.append((skill_md.parent.name, is_match))

    print(f"{'Skill':<16} {'REGEX MATCH'}")
    misses: list[str] = []
    for name, is_match in rows:
        is_label = "MATCH" if is_match else "MISS"
        print(f"{name:<16} {is_label}")
        if not is_match:
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
