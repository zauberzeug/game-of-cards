from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MigrateSharedWorktreeTreeResolutionTest(unittest.TestCase):
    """Regression: `goc migrate`'s filesystem operations must resolve both
    deck trees from DECK_ROOT, not REPO_ROOT, so a migrate from a linked
    worktree in shared-deck mode merges into and removes the PRIMARY tree's
    decks.

    Before the fix, `_cmd_migrate` built `canonical` and `legacy` from
    REPO_ROOT (the linked worktree): it copied legacy-only cards into the
    worktree's checkout copy of `.game-of-cards/deck/`, rmtree'd the
    worktree's checkout copy of `deck/`, printed "Migration complete" — and
    the shared primary deck kept both trees, so the dual-tree refusal kept
    firing on every subsequent goc invocation.
    """

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        env["GOC_WORKTREE_DECK"] = "shared"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

    def test_migrate_from_shared_worktree_operates_on_primary_trees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            primary = tmp / "primary"
            primary.mkdir()
            self._git(primary, "init", "-q")
            self._git(primary, "config", "user.email", "t@t")
            self._git(primary, "config", "user.name", "t")

            canonical = primary / ".game-of-cards" / "deck"
            canonical.mkdir(parents=True)
            (canonical / ".goc-version").write_text("0.0.0\n")
            legacy_card = primary / "deck" / "legacy-only-card"
            legacy_card.mkdir(parents=True)
            (legacy_card / "README.md").write_text("---\ntitle: legacy-only-card\n---\n")
            self._git(primary, "add", "-A")
            self._git(primary, "commit", "-q", "-m", "seed dual-tree deck")

            worktree = tmp / "linked"
            self._git(primary, "worktree", "add", "-q", "-b", "feature", str(worktree))

            result = self.run_goc(worktree, "migrate", "--yes")
            self.assertEqual(
                0,
                result.returncode,
                msg=f"goc migrate failed in shared-worktree mode.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )

            # The primary (shared) trees were merged and cleaned up.
            self.assertFalse((primary / "deck").exists(), "primary legacy deck/ not removed")
            self.assertTrue(
                (canonical / "legacy-only-card").is_dir(),
                "legacy-only card missing from primary canonical tree",
            )

            # The worktree's checkout copies were left alone.
            self.assertTrue(
                (worktree / "deck" / "legacy-only-card").is_dir(),
                "worktree checkout copy of deck/ was deleted",
            )
            self.assertFalse(
                (worktree / ".game-of-cards" / "deck" / "legacy-only-card").exists(),
                "card copied into the worktree's canonical tree",
            )

            # The dual-tree refusal is gone for subsequent invocations from
            # the worktree (validate may still flag the stub card's schema —
            # only the refusal matters here).
            follow_up = self.run_goc(worktree, "validate")
            self.assertNotIn(
                "two deck trees found",
                follow_up.stderr,
                msg=f"dual-tree refusal persists after migrate:\n{follow_up.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
