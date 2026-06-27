#!/usr/bin/env python3
"""Reproduce: `goc move` runs its git operations in the wrong tree under
shared-deck worktree mode.

Sets up a primary repo with a deck, adds a linked git worktree, enables
shared-deck mode, and from the linked worktree runs `goc move <old> <new>`.

Before the fix (`git mv` / `git ls-files` run with cwd=REPO_ROOT, the linked
worktree):
  - the `git mv` errors against deck paths outside that worktree; the error is
    swallowed and the code falls back to `shutil.move`, leaving the deck tree
    with a broken rename (`D old` + `?? new`, no `R`);
  - `git ls-files` from REPO_ROOT lists none of the deck files, so the moved
    card's own `title:` frontmatter is never rewritten and stays stale,
    failing `goc validate` (title != dir name).

After the fix both helpers resolve git cwd to DECK_ROOT (the primary tree
where the deck files are tracked), producing a clean `R` rename and a rewritten
`title:` field.

Exits non-zero before the fix, zero after.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


def goc(cwd: Path, *args: str, shared: bool = False) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    if shared:
        env["GOC_WORKTREE_DECK"] = "shared"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        primary = tmp / "primary"
        primary.mkdir()
        git(primary, "init", "-q")
        git(primary, "config", "user.email", "t@t")
        git(primary, "config", "user.name", "t")

        # Scaffold a card in the primary tree and commit so a worktree can branch.
        r = goc(primary, "new", "old-card-slug", "--gate", "none", "--tag", "story")
        if r.returncode != 0:
            print(f"setup: goc new failed:\n{r.stdout}\n{r.stderr}", file=sys.stderr)
            return 1
        git(primary, "add", "-A")
        git(primary, "commit", "-q", "-m", "seed")

        worktree = tmp / "linked"
        git(primary, "worktree", "add", "-q", "-b", "feature", str(worktree))

        # Move the card from the LINKED worktree in shared-deck mode.
        r = goc(worktree, "move", "old-card-slug", "new-card-slug", shared=True)
        if r.returncode != 0:
            print(f"goc move failed:\n{r.stdout}\n{r.stderr}", file=sys.stderr)
            return 1

        deck = primary / ".game-of-cards" / "deck"
        new_readme = deck / "new-card-slug" / "README.md"

        # 1) The moved card's own title: field must be rewritten.
        if not new_readme.exists():
            print("FAIL: new-card-slug/README.md does not exist", file=sys.stderr)
            return 1
        text = new_readme.read_text()
        if "title: old-card-slug" in text:
            print("FAIL: moved card still has stale 'title: old-card-slug'", file=sys.stderr)
            return 1
        if "title: new-card-slug" not in text:
            print("FAIL: moved card title was not rewritten to new-card-slug", file=sys.stderr)
            return 1

        # 2) The rename must be a tracked `R` in the deck (primary) tree,
        #    not a `D old` + `?? new` broken rename.
        status = git(primary, "status", "--porcelain").stdout
        if "old-card-slug" in status and "??" in status:
            print(f"FAIL: broken rename in deck tree:\n{status}", file=sys.stderr)
            return 1

        # 3) goc validate must pass (title == dir name).
        v = goc(primary, "validate")
        if v.returncode != 0:
            print(f"FAIL: goc validate failed after move:\n{v.stdout}\n{v.stderr}", file=sys.stderr)
            return 1

    print("OK: goc move produced a clean rename + rewritten title in shared-deck mode")
    return 0


if __name__ == "__main__":
    sys.exit(main())
