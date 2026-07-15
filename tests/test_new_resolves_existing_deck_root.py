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
