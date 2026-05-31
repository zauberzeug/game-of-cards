"""Reproduce: `goc attest` writes a passing `dod-100-percent` row for a card
with a free-form DoD, but `goc done` refuses the same card without `--force`.

Builds a throwaway repo with one card whose DoD is prose (no `[ ]` /
`[x]` items). Runs `goc attest`, then `goc done`. Compares the two
verbs' verdicts on the same predicate.

Expected today (defect present): `goc attest` exits 0 with a `[x]
dod-100-percent — freeform DoD` row and `Attestation OK.`; `goc done`
exits 2 with `ERROR: ... free-form DoD; use --force to bypass
enforcement`.

After fix: attest and done agree. Either both refuse / surface the
free-form DoD as unfit for an automated PASS, or both close the card
without the human override. The exact post-fix shape depends on which
of the three directions in the card's `## Decision required` section
was chosen.
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
summary: "test card with free-form DoD"
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
  Free-form prose DoD. No checkboxes. The work is done when the
  reviewer agrees the spike answered the question.
---

# Sample
"""


CONFIG_YAML = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: dod-100-percent
    kind: derived
workflow:
  auto_commit: false
"""


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-freeform-dod-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp, check=True)
        subprocess.run(["git", "config", "user.name", "T"], cwd=tmp, check=True)

        deck = tmp / ".game-of-cards" / "deck" / "sample-card"
        deck.mkdir(parents=True)
        (tmp / ".game-of-cards" / "config.yaml").write_text(CONFIG_YAML)
        (deck / "README.md").write_text(CARD_README)

        attest = _run(["attest", "sample-card", "--non-interactive"], tmp)
        print("--- goc attest ---")
        print(f"exit: {attest.returncode}")
        print("stdout:")
        print(attest.stdout)
        print("stderr:")
        print(attest.stderr)

        log_path = deck / "log.md"
        log_text = log_path.read_text() if log_path.exists() else ""
        print("--- log.md (verbatim) ---")
        print(log_text or "(absent)")

        done = _run(["done", "sample-card"], tmp)
        print("--- goc done ---")
        print(f"exit: {done.returncode}")
        print("stdout:")
        print(done.stdout)
        print("stderr:")
        print(done.stderr)

        attest_passed = (
            attest.returncode == 0
            and "Attestation OK." in attest.stdout
            and "[x] dod-100-percent" in log_text
            and "freeform DoD" in log_text
        )
        done_refused = done.returncode != 0 and "free-form DoD" in done.stderr

        defect_present = attest_passed and done_refused
        print(f"--- defect_present={defect_present} ---")
        if defect_present:
            print(
                "VERDICT: pre-fix. attest claims dod-100-percent PASSED "
                "(freeform DoD), but done refuses without --force. The "
                "two verbs disagree on the same predicate."
            )
            return 1

        if not attest_passed and not done_refused:
            print("VERDICT: post-fix. attest and done agree (both accept).")
            return 0
        if attest.returncode != 0 and done.returncode != 0:
            print("VERDICT: post-fix. attest and done agree (both refuse).")
            return 0

        print(
            "VERDICT: unexpected state — attest and done are not in the "
            "documented pre-fix shape, but they also do not agree. "
            f"attest exit={attest.returncode}, done exit={done.returncode}"
        )
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
