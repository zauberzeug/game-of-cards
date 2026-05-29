"""Reproduce: `goc new <child> --advances <parent>` leaves the parent
card's README as uncommitted ` M` in the worktree.

Empirical proof for
goc-new-with-advances-leaves-parent-card-mutation-uncommitted.

The script scaffolds a throwaway repo, installs goc into it, files a
parent and a wired child, and prints `git status --porcelain`.

Expected output (the bug):

  ?? .game-of-cards/deck/parent-card/             # after `goc new parent-card`
  ----- after parent commit + child filing -----
   M .game-of-cards/deck/parent-card/README.md    # the half-edge in flight
  ?? .game-of-cards/deck/child-card/

Exit code 0 = bug reproduced (parent README appears as modified after
the child filing). Exit code 1 = parent README is clean (bug fixed).
"""

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


REPO = _repo_root()


def _run(cmd, cwd, check=True):
    env = os.environ | {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    return subprocess.run(cmd, cwd=cwd, env=env, check=check,
                          capture_output=True, text=True)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="goc-half-edge-repro-"))
    try:
        _run(["git", "init", "-q"], cwd=tmp)
        _run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=tmp)

        # Install goc into the scratch repo via the source tree's uv project.
        _run(["uv", "--project", str(REPO), "run", "--quiet", "--no-sync",
              "goc", "install"], cwd=tmp)
        _run(["git", "add", "-A"], cwd=tmp)
        _run(["git", "commit", "-q", "-m", "scaffold"], cwd=tmp)

        _run(["uv", "--project", str(REPO), "run", "--quiet", "--no-sync",
              "goc", "new", "parent-card"], cwd=tmp)
        print("--- after `goc new parent-card` ---")
        print(_run(["git", "status", "--porcelain"], cwd=tmp).stdout, end="")
        _run(["git", "add", "-A"], cwd=tmp)
        _run(["git", "commit", "-q", "-m", "parent"], cwd=tmp)

        _run(["uv", "--project", str(REPO), "run", "--quiet", "--no-sync",
              "goc", "new", "child-card", "--advances", "parent-card"],
             cwd=tmp)
        status = _run(["git", "status", "--porcelain"], cwd=tmp).stdout
        print("--- after `goc new child-card --advances parent-card` ---")
        print(status, end="")

        # Bug condition: parent README appears as modified (` M ...`).
        parent_modified = any(
            line.startswith(" M") and "parent-card/README.md" in line
            for line in status.splitlines()
        )
        if parent_modified:
            print("\nBUG REPRODUCED: parent README hangs as ` M` "
                  "(half-edge in flight; an agent committing only "
                  "the new child dir ships a half-edge).")
            return 0
        else:
            print("\nFIXED: parent README is clean after child filing.")
            return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
