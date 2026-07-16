"""Reproduce: the deck-root fallback ancestor walk escapes a nested linked
worktree into the primary tree's deck without the shared-mode opt-in.

`_resolve_deck_root` (goc/engine.py) first runs the opt-in shared-worktree
gate (GOC_WORKTREE_DECK=shared / workflow.worktree_deck: shared). When that
declines, the fallback walk added by commit 3e17e3b3 scans cwd and every
filesystem ancestor for `.game-of-cards/`. For a linked worktree nested
INSIDE the primary tree (`git worktree add wt/feature`) with no deck of its
own, the walk crosses the worktree's own tree boundary, reaches the primary
root, and returns it — so `goc new` writes the card into the PRIMARY tree's
deck even though shared mode was never opted into (the closed spike card
pinned that sharing as opt-in only).

Exits 1 if `goc new` from the nested worktree succeeds and the card lands
in the primary tree's deck (defect present). Exits 0 if the command refuses
(no deck found from the worktree upward) and nothing is written cross-tree
(fix in place).
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


GOC_SRC = _repo_root()


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


with tempfile.TemporaryDirectory() as tmp:
    primary = Path(tmp) / "primary"
    primary.mkdir()
    git("init", "-q", cwd=primary)
    git("config", "user.email", "t@t", cwd=primary)
    git("config", "user.name", "t", cwd=primary)
    (primary / "f").write_text("hi\n")
    git("add", "f", cwd=primary)
    git("commit", "-qm", "init", cwd=primary)
    (primary / ".game-of-cards" / "deck").mkdir(parents=True)

    # Linked worktree nested INSIDE the primary tree — a common layout.
    git("worktree", "add", "-q", "wt/feature", "-b", "feature", cwd=primary)
    worktree = primary / "wt" / "feature"

    env = {k: v for k, v in os.environ.items() if k != "GOC_WORKTREE_DECK"}
    env["PYTHONPATH"] = str(GOC_SRC)
    result = subprocess.run(
        [sys.executable, "-m", "goc.cli", "new", "nested-worktree-card",
         "--gate", "none", "--tag", "bug"],
        cwd=worktree, env=env, capture_output=True, text=True,
    )

    in_primary = (primary / ".game-of-cards" / "deck" / "nested-worktree-card").is_dir()
    in_worktree = (worktree / ".game-of-cards" / "deck" / "nested-worktree-card").is_dir()

    print(f"goc new exit code: {result.returncode}")
    print(f"card dir exists under PRIMARY tree: {in_primary}")
    print(f"card dir exists under worktree:     {in_worktree}")

    if in_primary:
        print("DEFECT: nested worktree silently wrote into the primary tree's deck")
        sys.exit(1)
    if result.returncode != 0 and not in_worktree:
        print("OK: goc new refused — no cross-tree write without shared-mode opt-in")
        sys.exit(0)
    print(f"UNEXPECTED: rc={result.returncode} stderr={result.stderr.strip()!r}")
    sys.exit(1)
