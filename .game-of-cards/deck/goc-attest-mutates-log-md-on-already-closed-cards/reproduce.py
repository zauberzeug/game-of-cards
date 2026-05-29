"""Reproduce: `goc attest` runs on a card whose status is already terminal.

Constructs a throwaway deck containing a single `done` card, then invokes
`goc attest` against it. The defect: the verb returns 0, appends a fresh
"Closure verification" block to `log.md`, and prints a "Next: goc done"
hint — none of which is appropriate for a card that closed N days ago.

Run via `uv run python .game-of-cards/deck/goc-attest-mutates-log-md-on-already-closed-cards/reproduce.py`.
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


REPO_ROOT = _repo_root()


CARD_README = """\
---
title: dummy-closed-card
summary: "A closed card used to reproduce the goc-attest closed-card defect."
status: done
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: "2026-01-02T00:00:00Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: closed
---

# dummy-closed-card

Closed for reproduction purposes.
"""

CARD_LOG = """\
## 2026-01-02T00:00:00Z: closure

Closed.
"""

CONFIG_YAML = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
  - name: dod-100-percent
    kind: derived
  - name: log-md-closure-entry
    kind: derived
workflow:
  auto_commit: false
"""


def main() -> int:
    workdir = Path(tempfile.mkdtemp(prefix="goc-attest-repro-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.email", "x@y"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.name", "x"], cwd=workdir, check=True)
        (workdir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        deck_dir = workdir / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)
        (workdir / ".game-of-cards" / "config.yaml").write_text(CONFIG_YAML)
        card = deck_dir / "dummy-closed-card"
        card.mkdir()
        (card / "README.md").write_text(CARD_README)
        log = card / "log.md"
        log.write_text(CARD_LOG)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        log_before = log.read_text()

        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "attest", "dummy-closed-card", "--non-interactive"],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )
        log_after = log.read_text()

        print("=" * 72)
        print("goc attest dummy-closed-card  (card status: done)")
        print("=" * 72)
        print("exit code:", result.returncode)
        print()
        print("--- stdout ---")
        print(result.stdout)
        print("--- stderr ---")
        print(result.stderr)
        print("--- log.md before ---")
        print(log_before)
        print("--- log.md after ---")
        print(log_after)

        appended = len(log_after) > len(log_before)
        refused = (
            result.returncode != 0
            and "terminal" in (result.stderr + result.stdout).lower()
            and not appended
        )

        print("=" * 72)
        print("DEFECT CHECK")
        print("=" * 72)
        print(f"  card status:                       done (closed 2026-01-02)")
        print(f"  log.md mutated by attest verb:     {appended}")
        print(f"  verb refused with terminal-guard:  {refused}")
        if appended:
            print(
                "\nDEFECT REPRODUCED: `goc attest` mutates a closed card's log.md, "
                "appending a fresh 'Closure verification (<today>)' block. The "
                "sibling mutation verbs (`done`, `decide`, `status`) all refuse "
                "terminal targets; `attest` is the missing member of the family. "
                "The bad block lives in the closed card's historical record "
                "until a human removes it."
            )
            return 0
        print("\nNo defect — `goc attest` correctly refused to mutate the closed card.")
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
