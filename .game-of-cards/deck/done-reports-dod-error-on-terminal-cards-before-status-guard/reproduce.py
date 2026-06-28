"""Reproduce: `goc done` on a terminal card with unchecked DoD boxes
reports the DoD-incompleteness reason instead of the terminal-status
reason the code intends to emit.

Exits zero when the defect is FIXED (terminal-status message wins),
nonzero while the defect is present (DoD message shadows it).
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


ROOT = _repo_root()

DISPROVED_CARD_WITH_OPEN_DOD = """\
---
title: disproved-with-open-dod
summary: "Disproved fixture that still carries an unchecked DoD box."
status: disproved
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] PROCESS: this box was never checked because the card was disproved
---

# disproved-with-open-dod
"""


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        card_dir = cwd / ".game-of-cards" / "deck" / "disproved-with-open-dod"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(DISPROVED_CARD_WITH_OPEN_DOD)

        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "done", "disproved-with-open-dod"],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    print("exit code:", result.returncode)
    print("stderr:", result.stderr.strip())

    says_terminal = "(terminal)" in result.stderr
    says_dod = "unchecked DoD boxes" in result.stderr

    if says_dod and not says_terminal:
        print("\nDEFECT PRESENT: refused with the DoD-incompleteness message,")
        print("shadowing the authoritative terminal-status guard.")
        return 1
    if says_terminal and not says_dod:
        print("\nFIXED: refused with the authoritative terminal-status message.")
        return 0
    print("\nUNEXPECTED: neither/both messages present; inspect manually.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
