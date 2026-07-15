from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MoveSharedWorktreeGitCwdTest(unittest.TestCase):
    """Regression: `goc move`'s git operations must run in DECK_ROOT, not
    REPO_ROOT, so a move from a linked worktree in shared-deck mode produces a
    clean rename and rewrites the moved card's own `title:` field.

    Before the fix, `git mv` and `git ls-files` ran with cwd=REPO_ROOT (the
    linked worktree). The `git mv` failed against deck paths outside that tree
    (error swallowed → shutil.move fallback → broken `D old` + `?? new`
    rename), and `git ls-files` listed none of the deck files so the moved
    card's frontmatter `title:` stayed stale and failed `goc validate`.
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

    def _git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

    def _init_primary(self, primary: Path) -> None:
        self._git(primary, "init", "-q")
        self._git(primary, "config", "user.email", "t@t")
        self._git(primary, "config", "user.name", "t")
        (primary / ".game-of-cards" / "deck").mkdir(parents=True)
        self.assertEqual(
            0,
            self.run_goc(primary, "new", "old-card-slug", "--gate", "none", "--tag", "story").returncode,
        )
        self._git(primary, "add", "-A")
        self._git(primary, "commit", "-q", "-m", "seed")

    def test_move_from_shared_worktree_renames_cleanly_and_rewrites_title(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            primary = tmp / "primary"
            primary.mkdir()
            self._init_primary(primary)

            worktree = tmp / "linked"
            self._git(primary, "worktree", "add", "-q", "-b", "feature", str(worktree))

            result = self.run_goc(
                worktree, "move", "old-card-slug", "new-card-slug", shared=True,
            )
            self.assertEqual(
                0,
                result.returncode,
                msg=f"goc move failed in shared-worktree mode.\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )

            deck = primary / ".game-of-cards" / "deck"
            new_readme = deck / "new-card-slug" / "README.md"
            self.assertTrue(new_readme.exists(), "moved card README missing in primary deck")
            self.assertFalse((deck / "old-card-slug").exists(), "old card dir left behind")

            text = new_readme.read_text()
            self.assertNotIn("title: old-card-slug", text, "stale title left in moved card")
            self.assertIn("title: new-card-slug", text, "moved card title not rewritten")

            # The rename is tracked (no broken `D old` + `?? new` in the deck tree).
            status = self._git(primary, "status", "--porcelain").stdout
            self.assertNotIn("?? .game-of-cards/deck/new-card-slug/", status, f"untracked new dir:\n{status}")

            # title == dir name, so validate passes.
            self.assertEqual(
                0,
                self.run_goc(primary, "validate").returncode,
                "goc validate failed after shared-worktree move",
            )


if __name__ == "__main__":
    unittest.main()
