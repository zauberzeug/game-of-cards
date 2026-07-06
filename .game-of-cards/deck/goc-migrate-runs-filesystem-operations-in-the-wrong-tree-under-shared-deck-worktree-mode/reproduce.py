"""Reproduce: `goc migrate` merges/deletes the linked worktree's deck trees
instead of the shared primary deck under shared-deck-worktree mode.

Setup: a primary repo carrying BOTH `.game-of-cards/deck/` and a legacy
`deck/` (the dual-tree conflict `goc migrate` exists to fix), a linked git
worktree, and `GOC_WORKTREE_DECK=shared` so DECK_ROOT resolves to the
primary tree. Run `goc migrate --yes` from the linked worktree.

Expected (fixed): the legacy-only card lands in the primary tree's
`.game-of-cards/deck/`, the primary `deck/` is removed, and the dual-tree
conflict is gone for every subsequent goc invocation.

Actual (defect): `_cmd_migrate` resolves both trees from REPO_ROOT
(engine.py:6123-6124), so it copies into the WORKTREE's canonical tree,
rmtree's the WORKTREE's checkout copy of `deck/`, prints "Migration
complete" — and the shared primary deck still has both trees, so the
dual-tree refusal keeps firing.

Exits non-zero while the defect fires; zero once fixed.
"""
import os
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


REPO = _repo_root()


def sh(*cmd, cwd, env=None):
    return subprocess.run(
        cmd, cwd=str(cwd), env=env, capture_output=True, text=True, check=False
    )


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        primary = Path(td) / "primary"
        primary.mkdir()
        sh("git", "init", "-q", "-b", "main", cwd=primary)
        sh("git", "-C", str(primary), "config", "user.email", "t@t", cwd=primary)
        sh("git", "-C", str(primary), "config", "user.name", "t", cwd=primary)

        canonical = primary / ".game-of-cards" / "deck"
        canonical.mkdir(parents=True)
        (canonical / ".goc-version").write_text("0.0.0\n")
        legacy_card = primary / "deck" / "legacy-only-card"
        legacy_card.mkdir(parents=True)
        (legacy_card / "README.md").write_text("---\ntitle: legacy-only-card\n---\n")
        sh("git", "add", "-A", cwd=primary)
        sh("git", "commit", "-qm", "seed dual-tree deck", cwd=primary)

        worktree = Path(td) / "linked"
        r = sh("git", "worktree", "add", "-q", str(worktree), "-b", "wt", cwd=primary)
        if r.returncode != 0:
            print("SETUP FAILURE: git worktree add failed:", r.stderr)
            return 2

        env = dict(os.environ)
        env["GOC_WORKTREE_DECK"] = "shared"
        env["PYTHONPATH"] = str(REPO)
        r = sh(
            sys.executable, "-m", "goc.cli", "migrate", "--yes",
            cwd=worktree, env=env,
        )
        print("--- goc migrate (from linked worktree, shared deck mode) ---")
        print(r.stdout.strip())
        if r.stderr.strip():
            print(r.stderr.strip())

        primary_legacy_gone = not (primary / "deck").exists()
        primary_has_card = (canonical / "legacy-only-card").is_dir()
        worktree_legacy_gone = not (worktree / "deck").exists()
        worktree_got_card = (
            worktree / ".game-of-cards" / "deck" / "legacy-only-card"
        ).is_dir()

        print()
        print(f"primary deck/ removed (expected True):        {primary_legacy_gone}")
        print(f"primary canonical got the card (expected True): {primary_has_card}")
        print(f"worktree deck/ checkout deleted instead:      {worktree_legacy_gone}")
        print(f"worktree canonical got the card instead:      {worktree_got_card}")

        # A follow-up goc invocation still sees the shared deck's dual-tree
        # conflict — migrate reported success but fixed nothing it manages.
        r2 = sh(
            sys.executable, "-m", "goc.cli", "validate",
            cwd=worktree, env=env,
        )
        conflict_persists = "both" in (r2.stderr + r2.stdout).lower() or r2.returncode != 0
        print(f"subsequent goc still refuses on dual-tree:    {conflict_persists}")

        if primary_legacy_gone and primary_has_card:
            print("\nOK: migrate operated on the shared primary deck (fixed).")
            return 0
        print("\nDEFECT: migrate mutated the worktree's trees; shared deck untouched.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
