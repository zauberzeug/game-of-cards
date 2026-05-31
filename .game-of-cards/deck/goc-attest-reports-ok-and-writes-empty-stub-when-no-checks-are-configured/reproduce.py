"""Reproduce: `goc attest` writes an empty closure stub and reports OK when
both `layer_2_project_dod` and `layer_3_goc_dod` are configured as `[]`.

Builds a throwaway repo with a single card and a config in which both check
layers are empty. Runs `goc attest` and prints the verbatim log.md contents.

Expected output today (defect present): "Attestation OK." plus a bare
`## Closure verification (TIMESTAMP)` header in log.md.

After fix: `goc attest` either refuses the call or no-ops without writing to
log.md — log.md stays empty (or absent) and the exit code/print line match
the chosen contract.
"""

from __future__ import annotations

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
sys.path.insert(0, str(REPO_ROOT))


CARD_README = """\
---
title: sample-card
summary: "test card"
status: open
stage: null
contribution: low
created: 2026-05-31
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: []
definition_of_done: |
  - [ ] x
---

# Sample
"""


CONFIG_YAML = """\
layer_2_project_dod: []
layer_3_goc_dod: []
workflow:
  auto_commit: false
"""


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-attest-empty-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp, check=True)

        deck = tmp / ".game-of-cards" / "deck" / "sample-card"
        deck.mkdir(parents=True)
        (tmp / ".game-of-cards" / "config.yaml").write_text(CONFIG_YAML)
        (deck / "README.md").write_text(CARD_README)

        env = {"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"}
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "attest", "sample-card", "--non-interactive"],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
        )
        print("--- stdout ---")
        print(result.stdout)
        print("--- stderr ---")
        print(result.stderr)
        print(f"--- exit code: {result.returncode} ---")

        log_path = deck / "log.md"
        if log_path.exists():
            print("--- log.md (verbatim) ---")
            print(log_path.read_text())
        else:
            print("--- log.md does not exist (fix landed) ---")

        # Defect signature: exit zero, "Attestation OK." printed, and log.md
        # gained a "## Closure verification" header with no body rows.
        ok_printed = "Attestation OK." in result.stdout
        wrote_log = log_path.exists() and "## Closure verification" in log_path.read_text()
        has_rows = log_path.exists() and "Layer-" in log_path.read_text()

        defect_present = (
            result.returncode == 0
            and ok_printed
            and wrote_log
            and not has_rows
        )
        print(f"--- defect_present={defect_present} ---")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
