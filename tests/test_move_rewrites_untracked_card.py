from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MoveRewritesUntrackedCardTest(unittest.TestCase):
    """`goc move OLD NEW` must rewrite the moved card's own in-file slug
    (`title:`, `advances`/`advanced_by`, H1, cross-links) even when the card
    was never committed.

    Regression for goc-move-leaves-title-stale-on-uncommitted-cards: the move
    rewrite enumerated only `git ls-files` (tracked) output, so a freshly-filed
    card's untracked README.md was skipped — the directory got renamed (via the
    `shutil.move` fallback) while `title:` stayed stale, leaving a card that
    fails `goc validate`.
    """

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def _init_git_repo(self, cwd: Path) -> None:
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "t@t.t"],
            ["git", "config", "user.name", "t"],
        ):
            subprocess.run(args, cwd=cwd, check=True, capture_output=True)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)

    def _title_line(self, card_dir: Path) -> str:
        for ln in (card_dir / "README.md").read_text().splitlines():
            if ln.startswith("title:"):
                return ln.strip()
        return ""

    def _deck(self, cwd: Path) -> Path:
        return cwd / ".game-of-cards" / "deck"

    def test_untracked_card_move_rewrites_title(self) -> None:
        """The bug path: card created but never committed."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)
            self.run_goc(cwd, "new", "slug-with-typ0", "--contribution", "low", "--tag", "bug")
            # Do NOT commit — rename while the card is still untracked.
            mv = self.run_goc(cwd, "move", "slug-with-typ0", "slug-with-typo")
            self.assertEqual(0, mv.returncode, msg=mv.stderr)

            renamed = self._deck(cwd) / "slug-with-typo"
            self.assertTrue(renamed.is_dir())
            self.assertFalse((self._deck(cwd) / "slug-with-typ0").exists())
            self.assertEqual("title: slug-with-typo", self._title_line(renamed))

            validate = self.run_goc(cwd, "validate")
            combined = validate.stdout + validate.stderr
            self.assertNotIn("!=", combined, msg=f"title/dir mismatch survived:\n{combined}")

    def test_tracked_card_move_still_rewrites_title(self) -> None:
        """No-regression: a committed card must still rewrite correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)
            self.run_goc(cwd, "new", "tracked-slug-old", "--contribution", "low", "--tag", "bug")
            subprocess.run(["git", "add", "-A"], cwd=cwd, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-qm", "add card"], cwd=cwd, check=True, capture_output=True)

            mv = self.run_goc(cwd, "move", "tracked-slug-old", "tracked-slug-new")
            self.assertEqual(0, mv.returncode, msg=mv.stderr)

            renamed = self._deck(cwd) / "tracked-slug-new"
            self.assertEqual("title: tracked-slug-new", self._title_line(renamed))

    def test_untracked_sibling_cross_reference_is_rewritten(self) -> None:
        """An untracked sibling card that cross-references the moved slug in its
        body must also be rewritten — the broadened enumeration covers every
        untracked-not-ignored file, not just the moved card."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)
            self.run_goc(cwd, "new", "primary-old-slug", "--contribution", "low", "--tag", "bug")
            self.run_goc(cwd, "new", "sibling-card", "--contribution", "low", "--tag", "bug")
            sibling_readme = self._deck(cwd) / "sibling-card" / "README.md"
            sibling_readme.write_text(
                sibling_readme.read_text()
                + "\nSee [primary-old-slug](../primary-old-slug/) for context.\n"
            )
            # Neither card is committed.
            mv = self.run_goc(cwd, "move", "primary-old-slug", "primary-new-slug")
            self.assertEqual(0, mv.returncode, msg=mv.stderr)

            sibling_body = sibling_readme.read_text()
            self.assertIn("[primary-new-slug](../primary-new-slug/)", sibling_body)
            self.assertNotIn("primary-old-slug", sibling_body)


if __name__ == "__main__":
    unittest.main()
