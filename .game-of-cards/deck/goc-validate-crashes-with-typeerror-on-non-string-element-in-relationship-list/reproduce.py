"""Reproduce: `goc validate` crashes with `TypeError: unhashable type: 'list'`
when a relationship-list field contains a non-string list element.

Exit 1 today (validator crashes with a raw Python traceback); exit 0 after the
fix (validator reports a typed per-card error and exits non-zero with no
traceback).
"""
from __future__ import annotations

import os
import shutil
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
sys.path.insert(0, str(REPO))


CARD_NESTED_LIST = """---
title: test-card
status: open
stage: null
contribution: low
created: 2026-05-30
human_gate: none
tags: [api-contract]
advances:
  - good-target
  - [nested, list]
advanced_by: []
definition_of_done: |
  - [ ] do thing
---
# test-card
"""

CARD_GOOD = """---
title: good-target
status: open
stage: null
contribution: low
created: 2026-05-30
human_gate: none
tags: [api-contract]
advances: []
advanced_by: []
definition_of_done: |
  - [ ] do thing
---
# good-target
"""


def _scaffold_deck(root: Path) -> None:
    deck = root / ".game-of-cards" / "deck"
    deck.mkdir(parents=True)
    (deck / ".goc-version").write_text("0.0.21\n")
    (deck / "test-card").mkdir()
    (deck / "test-card" / "README.md").write_text(CARD_NESTED_LIST)
    (deck / "good-target").mkdir()
    (deck / "good-target" / "README.md").write_text(CARD_GOOD)


def main() -> int:
    tmp = Path(tempfile.mkdtemp())
    try:
        _scaffold_deck(tmp)
        env = {**os.environ, "PYTHONPATH": str(REPO)}
        proc = subprocess.run(
            [sys.executable, "-m", "goc.cli", "validate"],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
        )
        combined = proc.stdout + proc.stderr
        print("--- stdout/stderr ---")
        print(combined.rstrip())
        print(f"--- exit code: {proc.returncode} ---")

        crash_signature = (
            "TypeError: unhashable type: 'list'" in combined
            or "Traceback (most recent call last)" in combined
        )
        typed_error_signature = (
            "must be a list of strings" in combined
            or "advances:" in combined and "list" in combined and "string" in combined
        )

        if crash_signature:
            print("VERDICT: defect reproduces — validator crashed with raw traceback.")
            return 1
        if proc.returncode != 0 and typed_error_signature:
            print("VERDICT: fixed — validator reports typed per-card error.")
            return 0
        print("VERDICT: unexpected behavior — manual inspection required.")
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
