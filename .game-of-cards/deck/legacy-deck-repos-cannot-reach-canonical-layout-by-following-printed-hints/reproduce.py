"""Reproduce: a legacy-only deck cannot reach the canonical layout by following goc's hints.

Scaffolds a throwaway git repo with only the legacy layout — `deck/my-card/`
plus a `deck/.goc-version` sentinel, no `.game-of-cards/deck/` — and runs this
source tree's engine through the loop its own messages describe:

  goc validate   (control: must print the legacy warning naming `goc upgrade`)
  goc migrate    (says: run `goc install` first)
  goc install    (says: run `goc upgrade`)
  goc upgrade    (exit 0, "upgrade complete")
  goc migrate    (again)

Expected (after a fix): following the hints creates `.game-of-cards/deck/`
holding the card.
Defect: the loop ends where it started, with no canonical deck.

Exit codes: 0 = defect no longer fires (the canonical deck holds the card at
the end), 1 = defect fires (no canonical deck after the full loop), 2 = the
harness or a precondition is broken — the scaffold is not recognized as
legacy-only, or a command dies with a traceback. stdin is closed, so any
interactive prompt takes its non-interactive default. This repo's own deck
is never touched.

Run with:  uv run python .game-of-cards/deck/legacy-deck-repos-cannot-reach-canonical-layout-by-following-printed-hints/reproduce.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".game-of-cards").is_dir() and (p / "goc" / "engine.py").is_file():
            return p
        p = p.parent
    raise RuntimeError("goc source tree not found")


REPO = _repo_root()
LAUNCH = REPO / "goc" / "_launch.py"

CARD = """---
title: my-card
summary: A card in a legacy-layout deck.
status: open
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] TDD: placeholder
---

# My card
"""


def _goc(cwd: Path, home: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env["HOME"] = str(home)  # no host plugin cache or user config leaks in
    for var in ("GOC_WORKTREE_DECK", "CLAUDE_PLUGIN_ROOT", "GOC_WORKER"):
        env.pop(var, None)
    return subprocess.run(
        [sys.executable, str(LAUNCH), *args],
        cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
    )


def _first_line(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line.strip()
    return (text.strip().splitlines() or [""])[-1].strip()


def main() -> int:
    if not LAUNCH.is_file():
        print("PRECONDITION: goc/_launch.py missing from the checkout")
        return 2
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        repo, home = tmp / "consumer", tmp / "home"
        home.mkdir()
        (repo / "deck" / "my-card").mkdir(parents=True)
        (repo / "deck" / "my-card" / "README.md").write_text(CARD)
        (repo / "deck" / "my-card" / "log.md").write_text("")
        (repo / "deck" / ".goc-version").write_text("0.0.20\n")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        canonical = repo / ".game-of-cards" / "deck"

        ctl = _goc(repo, home, "validate")
        warned = "legacy deck/ location" in ctl.stderr + ctl.stdout
        print(f"control: goc validate -> exit {ctl.returncode}, legacy warning printed: {warned}")
        if not warned:
            print("HARNESS BROKEN: the scaffold is not treated as a legacy-only deck")
            return 2
        print(f"  {_first_line(ctl.stderr + ctl.stdout, 'legacy deck/')}")

        steps = [
            ("migrate", "goc install"),
            ("install", "goc upgrade"),
            ("upgrade", "upgrade complete"),
            ("migrate", "goc install"),
        ]
        for verb, needle in steps:
            res = _goc(repo, home, verb)
            out = res.stdout + res.stderr
            print(f"goc {verb:8} -> exit {res.returncode}; .game-of-cards/deck exists: {canonical.is_dir()}")
            print(f"  {_first_line(out, needle)}")
            if "Traceback (most recent call last)" in out:
                print(f"HARNESS BROKEN: goc {verb} died with a traceback:\n{out}")
                return 2

        migrated = (canonical / "my-card" / "README.md").is_file()
        legacy_left = (repo / "deck" / "my-card" / "README.md").is_file()
        sentinel = (repo / "deck" / ".goc-version")
        print(f"\nafter the loop: canonical card present: {migrated}; legacy card still in deck/: {legacy_left}")
        if sentinel.is_file():
            print(f"legacy sentinel deck/.goc-version now reads: {sentinel.read_text().strip()}")

    if migrated:
        print("\nDefect no longer fires: following the printed hints reached .game-of-cards/deck/.")
        return 0
    print("\nDEFECT PRESENT: migrate -> install -> upgrade -> migrate never creates .game-of-cards/deck/.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
