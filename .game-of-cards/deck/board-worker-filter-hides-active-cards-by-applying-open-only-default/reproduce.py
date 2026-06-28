#!/usr/bin/env python3
"""Reproduce: `goc --board --worker X` hides X's non-open cards.

Builds a temp deck with two `worker: alice` cards — one `open`, one
`active` — then runs the CLI three ways:

  * `--board --worker alice`            (the buggy invocation)
  * `--board`                           (no-worker control)
  * `--status all --board --worker alice` (the workaround)

The defect: the worker-scoped board consumes the `filtered` list, which
carries the implicit `status: open` default, so `alice-active-card`
vanishes from the ACTIVE column.

Exits non-zero while the defect fires; exits zero once fixed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

CARD = """\
---
title: {title}
summary: {title}
status: {status}
stage: null
contribution: low
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
worker: alice
definition_of_done: |
  - [x] test card
---

# {title}
"""


def run(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    pp = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pp else f"{ROOT}{os.pathsep}{pp}"
    proc = subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        for status in ("open", "active"):
            d = cwd / "deck" / f"alice-{status}-card"
            d.mkdir(parents=True)
            (d / "README.md").write_text(
                CARD.format(title=f"alice-{status}-card", status=status)
            )

        worker_board = run(cwd, "--board", "--worker", "alice", "--no-color")
        plain_board = run(cwd, "--board", "--no-color")
        all_board = run(cwd, "--status", "all", "--board", "--worker", "alice", "--no-color")

        ok = True

        # Controls: the active card IS visible without the worker filter,
        # and with the explicit `--status all` workaround.
        if "alice-active-card" not in plain_board:
            print("UNEXPECTED: --board (no worker) hid the active card")
            ok = False
        if "alice-active-card" not in all_board:
            print("UNEXPECTED: --status all --board --worker alice hid the active card")
            ok = False

        # The defect: worker-scoped board hides the active card.
        if "alice-active-card" not in worker_board:
            print("BUG: `goc --board --worker alice` hid alice-active-card "
                  "(ACTIVE column empty — open-only default leaked into the "
                  "worker-scoped board)")
            ok = False
        else:
            print("OK: worker-scoped board shows the active card")

        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
