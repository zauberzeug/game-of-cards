"""Reproducer: `goc validate` accepts `worker: {who: alice, where: "   "}` as valid.

Run from a clean checkout:

    uv run python .game-of-cards/deck/validate-accepts-whitespace-only-worker-where-as-non-empty/reproduce.py

Before the fix, prints `validate exit code: 0` and empty stderr.
After the fix, prints a nonzero exit and a stderr line of the form
`ws-where: worker: 'where' must be a non-empty, non-whitespace string`.
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
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()
sys.path.insert(0, str(ROOT))


CARD_BODY = """---
title: ws-where
summary: test card
status: open
stage: null
contribution: low
created: 2026-05-30
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
worker: {who: alice, where: "   "}
definition_of_done: |
  - [ ] PROCESS: test card
---

# ws-where
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        card_dir = cwd / ".game-of-cards" / "deck" / "ws-where"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(CARD_BODY)
        (card_dir / "log.md").write_text("")

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"

        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        print(f"validate exit code: {result.returncode}")
        print(f"validate stderr: {result.stderr.strip() or '(empty)'}")

        expected_msg = (
            "ws-where: worker: 'where' must be a non-empty, non-whitespace string"
        )
        if result.returncode != 0 and expected_msg in result.stderr:
            print("PASS: fix is in place (whitespace-only `where` rejected).")
            return 0
        print(
            "FAIL: validator accepts whitespace-only `where`. "
            f"Expected nonzero exit + stderr containing {expected_msg!r}."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
