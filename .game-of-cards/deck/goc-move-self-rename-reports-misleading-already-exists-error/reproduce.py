"""Reproduce: `goc move <X> <X>` reports a misleading "already exists" error.

Runs `goc move` in a throwaway temp deck (a real card renamed to itself)
and checks the stderr. The bug: the no-op self-rename trips the
`dst.exists()` collision guard because src and dst are the same path, so
it dies with `ERROR: ... already exists` instead of naming the real
condition (old title equals new title).

Exits 0 once the fix lands (stderr no longer claims a phantom collision);
exits 1 while the bug is present.
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


REPO_ROOT = _repo_root()

CARD = "sample-card-for-self-rename"
README = f"""---
title: {CARD}
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
  - [ ] placeholder
---

# {CARD}

body
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        card_dir = tmp / ".game-of-cards" / "deck" / CARD
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(README, encoding="utf-8")
        (card_dir / "log.md").write_text("", encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, "-m", "goc.cli", "move", CARD, CARD],
            cwd=str(tmp),
            env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
        )

    stderr = proc.stderr.strip()
    print(f"exit code : {proc.returncode}")
    print(f"stderr    : {stderr!r}")

    if "already exists" in stderr:
        print("\nBUG: self-rename reported a phantom collision ('already exists'),")
        print("     instead of naming the real condition (old title == new title).")
        return 1

    print("\nOK: self-rename no longer reports a phantom collision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
