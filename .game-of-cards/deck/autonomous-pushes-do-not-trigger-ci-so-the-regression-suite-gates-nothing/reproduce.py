"""Measure the gap between the last CI run on main and main's current head.

The defect is a GitHub Actions trigger rule, so it cannot be reproduced from
a local process alone. What this script does is make the citation set
re-checkable rather than a snapshot pasted into prose:

- the git half is deterministic and offline: how many commits sit on `main`
  after the last commit CI is recorded to have run on, and who authored them;
- the Actions half shells out to `gh` when it is available and authenticated,
  and prints the most recent `ci.yml` run so the recorded date can be
  re-confirmed (or shown to have moved, which is what closing this card
  should cause).

Exits 0 while the gap is open, 1 once CI has run on a commit at or after the
current head.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


ROOT = _repo_root()

# The last commit `ci.yml` is recorded to have run on: a human push on
# 2026-08-01. Every commit after it was pushed by the autonomous workflow.
LAST_CI_SHA = "0c6ac0a68949b5072aaa352e7740ac2c65c21fd1"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, text=True, capture_output=True, check=False
    ).stdout.strip()


def _gh_last_ci_run() -> dict | None:
    proc = subprocess.run(
        ["gh", "run", "list", "--workflow=ci.yml", "--branch", "main", "--limit", "1",
         "--json", "conclusion,createdAt,headSha,event"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        return None
    try:
        runs = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return runs[0] if runs else None


def main() -> int:
    trigger = (ROOT / ".github/workflows/ci.yml").read_text()
    block = trigger[trigger.index("\non:") + 1:].split("\njobs:")[0].strip()
    print("ci.yml trigger block (no paths filter — every push to main qualifies):")
    print("  " + "\n  ".join(block.splitlines()))
    print()

    if not _git("cat-file", "-t", LAST_CI_SHA):
        print(f"[SKIP] {LAST_CI_SHA[:8]} not in this clone (shallow checkout?)")
        return 0

    # Authors are bucketed bot / non-bot rather than named: this output is
    # quoted into the card body, and cards do not name individuals.
    log = _git("log", "--format=%H\t%an", f"{LAST_CI_SHA}..HEAD")
    commits = [ln.split("\t") for ln in log.splitlines() if ln]
    bot = sum(1 for _, author in commits if author.endswith("[bot]"))

    print(f"last commit CI is recorded to have run on : {LAST_CI_SHA[:8]} "
          f"({_git('log', '-1', '--format=%ad', '--date=short', LAST_CI_SHA)}, "
          "pushed with a human credential)")
    print(f"commits on main since it                  : {len(commits)}")
    print(f"of those, pushed by the autonomous bot    : {bot}")
    print()

    run = _gh_last_ci_run()
    if run is None:
        print("gh unavailable or unauthenticated — Actions half not re-checked; "
              "the recorded evidence is in this card's README.")
    else:
        print(f"most recent ci.yml run on main            : {run['createdAt']} "
              f"({run['event']}, {run['conclusion']}) on {run['headSha'][:8]}")
        if run["headSha"] == _git("rev-parse", "HEAD"):
            print("\nCI has run on the current head — the gap is closed.")
            return 1
        behind = _git("rev-list", "--count", f"{run['headSha']}..HEAD")
        print(f"current head is                           : {behind} commits ahead of it")

    print("\n[DEFECT] ci.yml has not run on any of these commits: pushes made with "
          "the default GITHUB_TOKEN do not start new workflow runs, so the "
          "regression suite gates nothing on the autonomous path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
