from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NewResolvesExistingDeckRootTest(unittest.TestCase):
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

    @staticmethod
    def make_deck(root: Path) -> None:
        (root / ".game-of-cards" / "deck").mkdir(parents=True)

    def test_new_from_nested_repo_uses_ancestor_deck(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            nested_repo = workspace / "repos" / "child"
            nested_repo.mkdir(parents=True)
            self.make_deck(workspace)
            subprocess.run(["git", "init", "-q"], cwd=nested_repo, check=True)

            result = self.run_goc(
                nested_repo,
                "new",
                "ancestor-deck-card",
                "--gate",
                "none",
                "--tag",
                "bug",
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            self.assertTrue(
                (workspace / ".game-of-cards" / "deck" / "ancestor-deck-card" / "README.md").is_file()
            )
            self.assertFalse((nested_repo / ".game-of-cards").exists())

    def test_nearest_ancestor_deck_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "outer"
            inner = outer / "inner"
            cwd = inner / "src"
            cwd.mkdir(parents=True)
            self.make_deck(outer)
            self.make_deck(inner)

            result = self.run_goc(
                cwd,
                "new",
                "nearest-deck-card",
                "--gate",
                "none",
                "--tag",
                "bug",
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            self.assertTrue(
                (inner / ".game-of-cards" / "deck" / "nearest-deck-card" / "README.md").is_file()
            )
            self.assertFalse(
                (outer / ".game-of-cards" / "deck" / "nearest-deck-card").exists()
            )

    def test_new_from_nested_worktree_refuses_without_shared_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            primary = Path(tmp) / "primary"
            primary.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=primary, check=True)
            subprocess.run(["git", "config", "user.email", "t@t"], cwd=primary, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=primary, check=True)
            (primary / "f").write_text("hi\n")
            subprocess.run(["git", "add", "f"], cwd=primary, check=True)
            subprocess.run(["git", "commit", "-qm", "init"], cwd=primary, check=True)
            self.make_deck(primary)
            subprocess.run(
                ["git", "worktree", "add", "-q", "wt/feature", "-b", "feature"],
                cwd=primary,
                check=True,
            )
            worktree = primary / "wt" / "feature"

            result = self.run_goc(
                worktree,
                "new",
                "nested-worktree-card",
                "--gate",
                "none",
                "--tag",
                "bug",
            )

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("no Game of Cards deck found", result.stderr)
            self.assertFalse(
                (primary / ".game-of-cards" / "deck" / "nested-worktree-card").exists()
            )
            self.assertFalse((worktree / ".game-of-cards").exists())

    def test_new_from_repo_nested_in_deck_owning_repo_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp) / "outer"
            inner = outer / "vendor" / "inner"
            inner.mkdir(parents=True)
            subprocess.run(["git", "init", "-q"], cwd=outer, check=True)
            subprocess.run(["git", "init", "-q"], cwd=inner, check=True)
            self.make_deck(outer)

            result = self.run_goc(
                inner,
                "new",
                "cross-repo-card",
                "--gate",
                "none",
                "--tag",
                "bug",
            )

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("no Game of Cards deck found", result.stderr)
            self.assertFalse(
                (outer / ".game-of-cards" / "deck" / "cross-repo-card").exists()
            )

    def test_new_without_installed_deck_fails_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(
                cwd,
                "new",
                "must-install-first",
                "--gate",
                "none",
                "--tag",
                "bug",
            )

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("no Game of Cards deck found", result.stderr)
            self.assertIn("goc install", result.stderr)
            self.assertFalse((cwd / ".game-of-cards").exists())


if __name__ == "__main__":
    unittest.main()
