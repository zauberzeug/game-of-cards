#!/usr/bin/env python3
"""Prove that a failed auto-commit leaves card files staged and still exits 0.

Builds a throwaway git repo, installs goc into it, plants a `pre-commit` hook
that rejects every commit (the same shape `.pre-commit-config.yaml` installs
for this repo's own `goc validate` / `card-language` guards), then runs
`goc publish` on an authored card and inspects three things:

  1. the verb's exit code and stdout,
  2. whether anything landed in git history,
  3. what `git diff --cached --name-only` reports afterwards.

Exits 0 when the defect is GONE (index clean after the failed commit), 1 while
it still fires — the `TDD: reproduce.py exits zero` DoD contract.
"""

from __future__ import annotations

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
CARD = "staged-index-probe"


def run(cmd: list[str], cwd: Path, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw)


def goc(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return run(["uv", "run", "--project", str(ROOT), "goc", *args], cwd)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "probe"
        repo.mkdir()

        run(["git", "init", "-q", "."], repo)
        run(["git", "config", "user.email", "probe@example.invalid"], repo)
        run(["git", "config", "user.name", "probe"], repo)

        if goc(["install", "--local-skills"], repo).returncode != 0:
            print("SETUP FAILED: goc install did not succeed")
            return 1
        run(["git", "add", "-A"], repo)
        run(["git", "commit", "-qm", "scaffold"], repo)

        # A pre-commit hook that refuses the commit. This is exactly what the
        # repo's own `goc validate` / `card-language` pre-commit hooks do to a
        # card that fails them, and `.pre-commit-config.yaml` notes that goc's
        # auto-commit shells out to `git commit` WITHOUT --no-verify, so the
        # hook fires on the auto-commit path.
        hook = repo / ".git" / "hooks" / "pre-commit"
        hook.write_text('#!/bin/sh\necho "pre-commit: rejected" >&2\nexit 1\n')
        hook.chmod(0o755)

        goc(["new", CARD, "--summary", "Probe."], repo)
        readme = repo / ".game-of-cards" / "deck" / CARD / "README.md"
        readme.write_text(
            readme.read_text()
            .replace("  - [ ] (replace with real criteria)\n", "  - [ ] MECHANICAL: authored.\n")
            .replace("(write the design doc here)", "Authored body.")
        )

        before = run(["git", "diff", "--cached", "--name-only"], repo).stdout.split()
        if before:
            print(f"SETUP FAILED: index not clean before the probe: {before}")
            return 1

        pub = goc(["publish", CARD], repo)
        after = run(["git", "diff", "--cached", "--name-only"], repo).stdout.split()
        log = run(["git", "log", "--oneline"], repo).stdout.strip().splitlines()

        print("index before `goc publish` : (clean)")
        print(f"goc publish exit code      : {pub.returncode}")
        print(f"goc publish stdout         : {pub.stdout.strip()!r}")
        print(f"commits in history         : {len(log)} ({log[-1] if log else '-'})")
        print(f"index after `goc publish`  : {after}")
        print()

        problems = []
        if after:
            problems.append(
                f"BUG: {len(after)} path(s) left staged by the failed auto-commit: {after}"
            )
        if pub.returncode == 0 and after:
            problems.append(
                "BUG: the verb exited 0 and printed its success line while nothing was committed"
            )
        if len(log) != 1:
            problems.append(f"UNEXPECTED: expected only the scaffold commit, found {len(log)}")

        if problems:
            for p in problems:
                print(p)
            print()
            print(
                "AGENTS.md § Parallel-Agent Commit Safety: \"before staging, run "
                "`git diff --cached --name-only`. If it lists files you did not "
                "stage, another agent is in its commit window\" — no agent is; "
                "these are orphans from a commit that already returned."
            )
            return 1

        print("PASS: the failed auto-commit left the index clean.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
