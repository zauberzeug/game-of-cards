"""Reproduce: `goc attest` runs on a card whose status is already terminal.

Builds a throwaway deck holding a single `done` card and runs
`goc attest --non-interactive` against it under two check configurations:

- one that includes `log-md-closure-entry`, which a closed card cannot pass on
  any day after its closure, so the stray block records a spurious FAIL;
- one whose checks all pass on the closed card, so attest exits 0 and prints
  its `Next: goc done <title>` hint for a card that closed long ago.

The defect fires when either run appends to the closed card's `log.md` or
prints the `Next: goc done` hint. Fixed means both runs are refused by the
terminal-status guard (exit 2, "(terminal)" on stderr) with `log.md`
byte-identical.

Exit codes: 0 = defect no longer fires, 1 = defect fires, 2 = harness or
precondition broken.

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

CLOSURE_ENTRY_CONFIG = """\
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

ALL_PASS_CONFIG = """\
layer_2_project_dod: []
layer_3_goc_dod:
  - name: advanced-by-closed
    kind: derived
  - name: dod-100-percent
    kind: derived
workflow:
  auto_commit: false
"""

SCENARIOS = (
    ("closure-entry check configured", CLOSURE_ENTRY_CONFIG),
    ("every configured check passes", ALL_PASS_CONFIG),
)


def _attest_closed_card(config: str) -> tuple[subprocess.CompletedProcess[str], str, str]:
    """Run `goc attest` on a fresh closed-card deck; return (result, log before, log after)."""
    workdir = Path(tempfile.mkdtemp(prefix="goc-attest-repro-"))
    try:
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.email", "x@y"], cwd=workdir, check=True)
        subprocess.run(["git", "config", "user.name", "x"], cwd=workdir, check=True)
        (workdir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0'\n")
        deck_dir = workdir / ".game-of-cards" / "deck"
        deck_dir.mkdir(parents=True)
        (workdir / ".game-of-cards" / "config.yaml").write_text(config)
        card = deck_dir / "dummy-closed-card"
        card.mkdir()
        (card / "README.md").write_text(CARD_README)
        log = card / "log.md"
        log.write_text(CARD_LOG)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        env.pop("GOC_WORKTREE_DECK", None)
        log_before = log.read_text()
        result = subprocess.run(
            [sys.executable, "-m", "goc.cli", "attest", "dummy-closed-card", "--non-interactive"],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )
        return result, log_before, log.read_text()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    verdicts: list[int] = []
    for label, config in SCENARIOS:
        try:
            result, log_before, log_after = _attest_closed_card(config)
        except (OSError, subprocess.CalledProcessError) as exc:
            print(f"HARNESS BROKEN ({label}): {exc}")
            return 2

        mutated = log_after != log_before
        hinted = "Next: goc done" in result.stdout
        refused = result.returncode == 2 and "(terminal)" in result.stderr

        print("=" * 72)
        print(f"goc attest dummy-closed-card  (card status: done; {label})")
        print("=" * 72)
        print("exit code:", result.returncode)
        print("--- stdout ---")
        print(result.stdout)
        print("--- stderr ---")
        print(result.stderr)
        if mutated:
            print("--- log.md after ---")
            print(log_after)
        print(f"  log.md mutated:              {mutated}")
        print(f"  'Next: goc done' printed:    {hinted}")
        print(f"  refused by terminal guard:   {refused}")
        print()

        if mutated or hinted:
            verdicts.append(1)
        elif refused:
            verdicts.append(0)
        else:
            verdicts.append(2)

    if 1 in verdicts:
        print(
            "DEFECT REPRODUCED: `goc attest` treats a closed card as attestable — it "
            "appends a fresh 'Closure verification (<today>)' block to the card's "
            "log.md and/or tells the caller to `goc done` a card that is already done."
        )
        return 1
    if 2 in verdicts:
        print(
            "HARNESS BROKEN: `goc attest` neither mutated the closed card nor refused it "
            "as terminal; inspect the output above."
        )
        return 2
    print("No defect — `goc attest` refused the closed card and left its log.md untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
