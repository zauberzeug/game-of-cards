"""Reproduce: `goc attest` records a passing attestation when every configured check is --skipped.

Constructs a throwaway deck with the goc-shipped default config (three layer-3
derived checks) and an open card carrying one unchecked DoD box, then runs
`goc attest --skip <name>` for every configured check. The defect: the verb
prints "Attestation OK", exits 0, and writes a `## Closure verification` block
to `log.md` whose rows are all `[~] SKIPPED` — i.e. an attestation that ran zero
real checks is recorded as passing. The empty-config guard that refuses to write
a "proves nothing" block only fires when the layer arrays are empty, not when
checks exist but are all skipped.

Run via `uv run python .game-of-cards/deck/goc-attest-reports-ok-when-every-configured-check-is-skipped/reproduce.py`.

Exit 0 == defect reproduced (before fix); exit 1 == defect absent (after fix).
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
title: sample-card
summary: "An open card used to reproduce the all-skipped attest defect."
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
  - [ ] not yet done
---

# sample-card

Open card for reproduction purposes.
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
    workdir = Path(tempfile.mkdtemp(prefix="goc-attest-allskip-repro-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.email", "x@y"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.name", "x"], cwd=workdir, check=True)
        (workdir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        deck_dir = workdir / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)
        (workdir / ".game-of-cards" / "config.yaml").write_text(CONFIG_YAML)
        card = deck_dir / "sample-card"
        card.mkdir()
        (card / "README.md").write_text(CARD_README)
        log = card / "log.md"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)

        log_before = log.read_text() if log.exists() else ""

        result = subprocess.run(
            [
                sys.executable, "-m", "goc.cli", "attest", "sample-card",
                "--skip", "advanced-by-closed",
                "--skip", "dod-100-percent",
                "--skip", "log-md-closure-entry",
                "--non-interactive",
            ],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )
        log_after = log.read_text() if log.exists() else ""

        print("=" * 72)
        print("goc attest sample-card --skip <all three configured checks>")
        print("=" * 72)
        print("exit code:", result.returncode)
        print()
        print("--- stdout ---")
        print(result.stdout)
        print("--- stderr ---")
        print(result.stderr)
        print("--- log.md after ---")
        print(log_after or "(log.md does not exist)")

        wrote_block = "## Closure verification" in log_after and not log_before
        said_ok = "Attestation OK." in result.stdout
        defect = result.returncode == 0 and said_ok and wrote_block

        print("=" * 72)
        print("DEFECT CHECK")
        print("=" * 72)
        print(f"  every configured check --skipped:  True")
        print(f"  exit code 0:                       {result.returncode == 0}")
        print(f"  printed 'Attestation OK.':         {said_ok}")
        print(f"  wrote Closure verification block:  {wrote_block}")
        if defect:
            print(
                "\nDEFECT REPRODUCED: `goc attest` recorded a passing attestation "
                "(exit 0, 'Attestation OK', a Closure verification block) when zero "
                "real checks ran — every configured check was skipped. This is the "
                "same 'proves nothing' outcome the empty-config guard refuses, "
                "reached through the --skip path."
            )
            return 0
        print(
            "\nNo defect — `goc attest` refused the all-skipped invocation "
            "(non-zero exit, no log.md mutation)."
        )
        return 1
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
