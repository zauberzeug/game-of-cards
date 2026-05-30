"""Verify the fix for the half-edge defect on `goc new --advances`.

The original defect: `goc new <child> --advances <parent>` writes the
parent's `advanced_by` edge to disk but never commits it, leaving the
parent README as ambient ` M` in the worktree. An agent that follows
AGENTS.md's explicit-pathspec rule and commits only the new card
directory ships a half-edge.

The fix (Option C from the card body): `goc new` gained `--commit` /
`--no-commit` flags matching the sibling edge verbs. Default remains
no-commit so today's scaffold-then-fill-in workflow is unchanged;
the canonical wired-filing path (recommended in
`Skill(create-card)` Step 4) uses `--commit` so both the new card
directory and the wired endpoint(s) land in a single atomic commit
and no half-edge can be shipped.

This script scaffolds a throwaway repo, installs goc into it, files
a parent (committed), then files a wired child with `--commit` and
prints `git status --porcelain`.

Expected output (the fix in place):

  ----- after `goc new child-card --advances parent-card --commit` -----
  (empty — the worktree is clean: both endpoints landed in one
  atomic commit; no half-edge can be shipped by a subsequent
  explicit-pathspec commit)

Exit code 0 = fix in place (worktree clean after wired filing).
Exit code 1 = defect still fires (parent README modified, or new
card untracked).
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
        _run(["git", "add", "-A"], cwd=tmp)
        _run(["git", "commit", "-q", "-m", "parent"], cwd=tmp)

        _run(["uv", "--project", str(REPO), "run", "--quiet", "--no-sync",
              "goc", "new", "child-card",
              "--advances", "parent-card", "--commit"],
             cwd=tmp)
        status = _run(["git", "status", "--porcelain"], cwd=tmp).stdout
        print("--- after `goc new child-card --advances parent-card --commit` ---")
        print(status if status else "(clean)")

        # Fix condition: the worktree is clean — both the new card
        # directory AND the parent README's edge mutation landed in one
        # atomic commit. No `M` on the parent README, no untracked
        # child-card directory.
        parent_dirty = any(
            "parent-card/README.md" in line for line in status.splitlines()
        )
        child_untracked = any(
            "child-card" in line for line in status.splitlines()
        )
        if parent_dirty or child_untracked:
            print("\nDEFECT STILL FIRES: worktree is not clean after "
                  "`goc new ... --commit`.")
            return 1
        print("\nFIX IN PLACE: worktree is clean — both endpoints "
              "committed atomically, no half-edge can be shipped.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
