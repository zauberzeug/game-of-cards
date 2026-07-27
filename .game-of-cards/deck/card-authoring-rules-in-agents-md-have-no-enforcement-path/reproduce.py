#!/usr/bin/env python3
"""Reproduce: the title guards pass a card title that plainly breaks
AGENTS.md's English-only card-authoring rule.

The title used here is the real one this repo carried from 2026-07-18 until a
refine-deck pass renamed it by hand on 2026-07-27. It is a well-formed slug —
lower-kebab, ASCII, no jargon tokens — so every guard in the filing path
accepts it.

Run from the repo root:

    uv run python .game-of-cards/deck/card-authoring-rules-in-agents-md-have-no-enforcement-path/reproduce.py

Exits 1 while the guards accept it, 0 once some guard rejects or flags it.
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


sys.path.insert(0, str(_repo_root()))

from goc import engine  # noqa: E402

# The title as it was actually filed. German: "OpenClaw plugin skills force
# multiple reads per session."
OFFENDER = "openclaw-plugin-skills-erzwingen-mehrfach-reads-pro-session"

# A control that the guard *does* catch, proving the scanner is alive — without
# this, an empty offender list would be indistinguishable from a dead check.
CONTROL = "r88-runSimulation-fails"


def main() -> int:
    hits = engine._check_title_antipatterns(OFFENDER)
    control_hits = engine._check_title_antipatterns(CONTROL)

    print(f"antipattern rules defined:   {len(engine.TITLE_ANTIPATTERNS)}")
    print(f"control title {CONTROL!r}")
    print(f"  -> {len(control_hits)} hit(s): {control_hits}")
    print(f"offending title {OFFENDER!r}")
    print(f"  -> {len(hits)} hit(s): {hits}")

    if not control_hits:
        print(
            "\nINCONCLUSIVE — the control title was not flagged either, so the "
            "scanner itself is broken and this run proves nothing about the "
            "English-only gap. Fix the control first."
        )
        return 1

    if hits:
        print(
            "\nOK — a guard now flags the non-English title; the English-only "
            "rule has an enforcement path."
        )
        return 0

    print(
        "\nFAIL — the guard is alive (it flags the control) and still accepts a "
        "title that breaks AGENTS.md's English-only rule. `goc new`, `goc move` "
        "and `goc quality-pass` all route through this same predicate, so none "
        "of them can catch it."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
