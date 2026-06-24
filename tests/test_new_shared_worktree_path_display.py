from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NewSharedWorktreePathDisplayTest(unittest.TestCase):
    """Regression: `goc new`'s success message must not crash when the deck
    lives in a shared worktree root (DECK_ROOT != REPO_ROOT).

    In shared-worktree-deck mode the deck resolves to the *primary* working
    tree while the command runs from a linked worktree. The new card_dir then
    lives outside REPO_ROOT (== cwd), so the final `relative_to(...)` display
    must be taken against DECK_ROOT — relative_to(REPO_ROOT) raises ValueError
    after the card is already on disk.
    """

    def run_goc(self, cwd: Path, *args: str, shared: bool = False) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        if shared:
            env["GOC_WORKTREE_DECK"] = "shared"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _git(self, cwd: Path, *args: str) -> None:
        subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

    def _init_primary(self, primary: Path) -> None:
        self._git(primary, "init", "-q")
        self._git(primary, "config", "user.email", "t@t")
        self._git(primary, "config", "user.name", "t")
        # Scaffold the deck in the primary tree and commit so a worktree can branch.
        self.assertEqual(
            0,
            self.run_goc(primary, "new", "seed-card", "--gate", "none", "--tag", "story").returncode,
        )
        self._git(primary, "add", "-A")
        self._git(primary, "commit", "-q", "-m", "seed")

    def test_new_from_shared_worktree_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            primary = tmp / "primary"
            primary.mkdir()
            self._init_primary(primary)

            worktree = tmp / "linked"
            self._git(primary, "worktree", "add", "-q", "-b", "feature", str(worktree))

            # Run `goc new` from the linked worktree in shared-deck mode. The
            # new card resolves under the primary tree's deck, NOT the cwd.
            result = self.run_goc(
                worktree, "new", "worktree-card", "--gate", "none", "--tag", "story",
                shared=True,
            )

            self.assertEqual(
                0,
                result.returncode,
                msg=f"goc new crashed in shared-worktree mode.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            self.assertNotIn("ValueError", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            # Path is displayed relative to the (shared) deck root.
            self.assertIn("created .game-of-cards/deck/worktree-card/", result.stdout)
            # The card landed in the PRIMARY tree's deck, not the linked worktree.
            self.assertTrue((primary / ".game-of-cards" / "deck" / "worktree-card" / "README.md").exists())
            self.assertFalse((worktree / ".game-of-cards" / "deck" / "worktree-card").exists())


if __name__ == "__main__":
    unittest.main()
