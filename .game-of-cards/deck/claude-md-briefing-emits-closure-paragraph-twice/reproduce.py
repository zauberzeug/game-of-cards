"""Demonstrate that `goc install --briefing-target CLAUDE.md` emits the
`Closure is not frozenness.` paragraph twice in the marker-bounded GoC
briefing block.

Run from the repo root:

    uv run python deck/claude-md-briefing-emits-closure-paragraph-twice/reproduce.py

Exits 1 (defect present) when CLAUDE.md briefing contains > 1 occurrence;
exits 0 (defect absent) when the duplicate has been removed.
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


def main() -> int:
    sys.path.insert(0, str(_repo_root()))
    from goc.install import _briefing_body, _templates_root

    templates = _templates_root()
    needle = "Closure is not frozenness"
    counts: dict[str, int] = {}
    for target in ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md"):
        body = _briefing_body(templates, target)
        counts[target] = body.count(needle)
        print(f'{target:<16}: {counts[target]} occurrence(s) of "{needle}"')

    claude_count = counts["CLAUDE.md"]
    print()
    if claude_count > 1:
        print(f"DEFECT PRESENT — CLAUDE.md briefing carries the paragraph {claude_count}x.")
        return 1
    print("DEFECT ABSENT — CLAUDE.md briefing carries the paragraph exactly once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
