"""Reproduce: `goc migrate` rmtrees the legacy deck/ with NO confirm prompt
when the legacy tree holds only loose files (no card subdirectories) and a
canonical .game-of-cards/deck/ also exists (dual-tree conflict).

Setup: a sentinel-gated legacy deck/ whose card subdirs were already moved to
the canonical tree, leaving only deck/.goc-version + deck/NOTES.txt. Both trees
exist, so _DUAL_TREE_CONFLICT is True. We run `goc migrate` WITHOUT --auto-yes
and feed empty stdin. `confirm()` reads from stdin in non-tty mode and returns
its default (False) on empty input, so IF the confirm gate fired the migrate
would abort (exit 1) and the loose files would survive. Instead the gate is
skipped entirely and rmtree(legacy) runs unconditionally.

Expected on a buggy checkout: exit 0, no prompt, deck/ and its loose files GONE.
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


REPO = _repo_root()

CANONICAL_CARD = """\
---
title: real-card
summary: "x"
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
  - [ ] TDD: x
---
# real-card
body
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        canonical = repo / ".game-of-cards" / "deck" / "real-card"
        canonical.mkdir(parents=True)
        (canonical / "README.md").write_text(CANONICAL_CARD)
        (canonical / "log.md").write_text("")

        # Legacy deck/ with ONLY loose files — no card subdirectories.
        legacy = repo / "deck"
        legacy.mkdir()
        (legacy / ".goc-version").write_text("0.0.0\n")
        (legacy / "NOTES.txt").write_text("keep me\n")

        notes = legacy / "NOTES.txt"
        print("before: legacy deck/ exists:", legacy.is_dir())
        print("before: NOTES.txt exists:   ", notes.is_file())

        proc = subprocess.run(
            [sys.executable, "-m", "goc.cli", "migrate"],
            cwd=str(repo),
            env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
            input="",  # empty stdin: confirm() default is False -> would abort
            capture_output=True,
            text=True,
        )
        print("\n--- migrate stdout ---")
        print(proc.stdout.rstrip())
        if proc.stderr.strip():
            print("--- migrate stderr ---")
            print(proc.stderr.rstrip())
        print(f"--- exit={proc.returncode} ---\n")

        legacy_gone = not legacy.exists()
        notes_gone = not notes.exists()
        prompt_shown = "?" in proc.stdout and "[y/N]" in proc.stdout

        print("after: legacy deck/ removed:   ", legacy_gone)
        print("after: NOTES.txt destroyed:    ", notes_gone)
        print("confirm prompt shown to user:  ", prompt_shown)

        defect = legacy_gone and notes_gone and not prompt_shown
        print()
        if defect:
            print(
                "DEFECT CONFIRMED: `goc migrate` deleted the legacy deck/ and its "
                "loose files with no confirmation prompt and without --auto-yes."
            )
            return 1
        print(
            "OK: the confirm gate fired (or the tree survived) — defect not present."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
