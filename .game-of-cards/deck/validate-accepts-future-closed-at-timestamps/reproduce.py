"""Reproduce: `goc validate` accepts `closed_at` ~73 years in the future.

Builds a scratch deck containing one terminal card whose `closed_at` is
"2099-12-31T00:00:00Z", runs `goc validate` against it, and asserts the
validator returns exit 0 (no temporal-ordering check). Exits 0 when the
defect fires, 1 when the validator catches it.
"""

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


SAMPLE_README = """---
title: sample-future-closed
summary: "Sample for future closed_at check."
status: done
stage: null
contribution: low
created: 2026-05-30
closed_at: "2099-12-31T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [x] (sample)
---

# sample
"""


def main() -> int:
    repo = _repo_root()
    with tempfile.TemporaryDirectory() as scratch:
        deck = Path(scratch) / ".game-of-cards" / "deck" / "sample-future-closed"
        deck.mkdir(parents=True)
        (deck / "README.md").write_text(SAMPLE_README)
        (deck / "log.md").write_text("")

        env = os.environ.copy()
        env["PYTHONPATH"] = str(repo)

        print(f"created sample card with closed_at=2099-12-31T00:00:00Z")
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "validate"],
            cwd=scratch,
            env=env,
            capture_output=True,
            text=True,
        )
        print(f"goc validate exit code: {result.returncode}")
        tail = result.stdout.strip().splitlines()[-3:]
        print("goc validate output (tail):")
        for line in tail:
            print(f"  {line}")

        if result.returncode == 0:
            print("DEFECT: validator accepts closed_at ~73 years in the future")
            return 0
        print("FIXED: validator rejected the future closed_at")
        return 1


if __name__ == "__main__":
    sys.exit(main())
