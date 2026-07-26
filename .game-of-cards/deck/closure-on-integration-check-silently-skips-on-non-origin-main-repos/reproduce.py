"""Offline reproduction: `workflow.closure_on_integration` hardcodes
`git fetch origin main` / `origin/main`, so on a repo whose canonical
branch is `master` the fetch always fails, the guard warns-and-skips,
and an unintegrated card closes as `done` with exit 0. The identical
setup with canonical branch `main` blocks the close with exit 2.

Run: uv run python .game-of-cards/deck/closure-on-integration-check-silently-skips-on-non-origin-main-repos/reproduce.py
Exits non-zero while the defect fires.
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


CARD_README = """\
---
title: policy-test-card
summary: "Card used to probe the closure_on_integration guard."
status: active
stage: null
contribution: medium
created: 2026-07-24
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] MECHANICAL: probe card, DoD complete by construction
---

# policy-test-card

Probe card for the closure_on_integration guard.
"""

CONFIG = """\
workflow:
  closure_on_integration: true
"""


def close_unintegrated_card(root: Path, tmp: Path, branch: str) -> subprocess.CompletedProcess:
    """Build a bare remote with canonical branch `branch`, clone it, commit an
    unpushed DoD-complete card, and attempt `goc done` on it."""
    remote = tmp / f"remote-{branch}.git"
    work = tmp / f"work-{branch}"
    git_env = dict(
        os.environ,
        PYTHONPATH=str(root),
        GIT_AUTHOR_NAME="probe",
        GIT_AUTHOR_EMAIL="probe@example.com",
        GIT_COMMITTER_NAME="probe",
        GIT_COMMITTER_EMAIL="probe@example.com",
    )

    def git(*argv, cwd):
        subprocess.run(["git", *argv], cwd=cwd, env=git_env,
                       check=True, capture_output=True, text=True)

    subprocess.run(["git", "init", "-q", "--bare", "-b", branch, str(remote)],
                   check=True, capture_output=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(work)],
                   check=True, capture_output=True)

    card_dir = work / ".game-of-cards" / "deck" / "policy-test-card"
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(CARD_README)
    (card_dir / "log.md").write_text("")
    (work / ".game-of-cards" / "config.yaml").write_text(CONFIG)

    git("add", ".", cwd=work)
    git("commit", "-q", "-m", "seed remote", cwd=work)
    git("push", "-q", "origin", branch, cwd=work)

    # One more commit that never reaches the remote: HEAD is now NOT
    # reachable from any origin/* ref, i.e. the work is unintegrated.
    (work / "unintegrated.txt").write_text("local-only work\n")
    git("add", "unintegrated.txt", cwd=work)
    git("commit", "-q", "-m", "unintegrated work", cwd=work)

    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "done", "policy-test-card"],
        cwd=work, env=git_env, capture_output=True, text=True,
    )


def main() -> int:
    root = _repo_root()
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)

        control = close_unintegrated_card(root, tmp, "main")
        blocked = control.returncode == 2 and "not" in control.stderr
        print(f"[1] canonical branch `main`, unpushed HEAD -> `goc done` exit "
              f"{control.returncode} (policy blocks the close): {blocked}")

        probe = close_unintegrated_card(root, tmp, "master")
        skipped = "skipping check" in probe.stderr
        print(f"[2] canonical branch `master`, unpushed HEAD -> `goc done` exit "
              f"{probe.returncode}; stderr says 'skipping check': {skipped}")

        if blocked and probe.returncode == 0 and skipped:
            print("[FAIL] the opt-in integration policy silently no-ops on a "
                  "master-branch repo: identical unintegrated work closes as done")
            return 1
        print("[OK] closure_on_integration enforces on non-origin/main repos "
              "(or fails loudly instead of skipping)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
