from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NewWiresEdgesTest(unittest.TestCase):
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

    def assert_goc_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
        )

    def readme(self, cwd: Path, title: str) -> str:
        return (cwd / ".game-of-cards" / "deck" / title / "README.md").read_text()

    def test_new_repeatable_edge_flags_write_both_sides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for title in ("target-one", "target-two", "parent-one", "parent-two"):
                self.assert_goc_ok(self.run_goc(cwd, "new", title, "--gate", "none", "--tag", "story"))

            created = self.run_goc(
                cwd,
                "new",
                "linked-card",
                "--gate",
                "none",
                "--tag",
                "story",
                "--advances",
                "target-one",
                "--advances",
                "target-two",
                "--advanced-by",
                "parent-one",
                "--advanced-by",
                "parent-two",
            )

            self.assert_goc_ok(created)
            linked = self.readme(cwd, "linked-card")
            self.assertIn("advances:\n  - target-one\n  - target-two\n", linked)
            self.assertIn("advanced_by:\n  - parent-one\n  - parent-two\n", linked)
            self.assertIn("advanced_by:\n  - linked-card\n", self.readme(cwd, "target-one"))
            self.assertIn("advanced_by:\n  - linked-card\n", self.readme(cwd, "target-two"))
            self.assertIn("advances:\n  - linked-card\n", self.readme(cwd, "parent-one"))
            self.assertIn("advances:\n  - linked-card\n", self.readme(cwd, "parent-two"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_new_missing_edge_target_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "new", "known-card", "--gate", "none", "--tag", "story"))

            result = self.run_goc(
                cwd,
                "new",
                "missing-link-card",
                "--gate",
                "none",
                "--tag",
                "story",
                "--advances",
                "known-card",
                "--advanced-by",
                "missing-card",
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("referenced card(s) not found: missing-card", result.stderr)
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "missing-link-card").exists())
            self.assertNotIn("missing-link-card", self.readme(cwd, "known-card"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_new_cycle_rejection_creates_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "new", "child-card", "--gate", "none", "--tag", "story"))
            self.assert_goc_ok(self.run_goc(cwd, "advance", "child-card", "--by", "parent-card", "--no-commit"))

            result = self.run_goc(
                cwd,
                "new",
                "cycle-card",
                "--gate",
                "none",
                "--tag",
                "story",
                "--advances",
                "parent-card",
                "--advanced-by",
                "child-card",
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("would create a cycle in the advances graph", result.stderr)
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "cycle-card").exists())
            self.assertNotIn("cycle-card", self.readme(cwd, "parent-card"))
            self.assertNotIn("cycle-card", self.readme(cwd, "child-card"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_new_help_lists_edge_flags_with_examples(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_goc(Path(tmp), "new", "--help")

            self.assert_goc_ok(result)
            self.assertIn("--advances TITLE", result.stdout)
            self.assertIn("--advanced-by TITLE", result.stdout)
            self.assertIn("--commit", result.stdout)
            self.assertIn("--no-commit", result.stdout)
            self.assertIn("goc new child-card --advances parent-card", result.stdout)
            self.assertIn("goc new child-card --advanced-by parent-card", result.stdout)

    def _init_git_repo(self, cwd: Path) -> None:
        subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)
        # Identity required for commits in CI environments that don't ship
        # a default git user.
        subprocess.run(["git", "config", "user.email", "t@t"], cwd=cwd, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=cwd, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "init"], cwd=cwd, check=True)

    def _git_status(self, cwd: Path) -> str:
        return subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def test_new_with_commit_flag_commits_both_endpoints_and_new_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)

            # Scaffold the parent card and commit it so the next `goc new
            # --advances parent --commit` runs against a clean worktree.
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "parent"], cwd=cwd, check=True)

            # The defect: without --commit, the parent's edge mutation
            # lingers as ambient ` M` in the worktree.
            self.assertEqual(self._git_status(cwd), "")
            self.assert_goc_ok(self.run_goc(
                cwd, "new", "child-card",
                "--gate", "none", "--tag", "story",
                "--advances", "parent-card",
                "--commit",
            ))
            status = self._git_status(cwd)

            # --commit closes the half-edge: the parent's README mutation
            # AND the new card directory are committed atomically.
            self.assertNotIn("parent-card/README.md", status)
            self.assertNotIn("child-card", status)
            self.assertEqual(status, "")

    def test_new_default_does_not_commit(self) -> None:
        # Option C's contract: the default `goc new` (no --commit flag)
        # preserves today's scaffold-then-fill-in behavior — neither the
        # new card directory nor any edge endpoints are committed.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._init_git_repo(cwd)
            self.assert_goc_ok(self.run_goc(cwd, "new", "parent-card", "--gate", "none", "--tag", "story"))
            subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "parent"], cwd=cwd, check=True)

            self.assert_goc_ok(self.run_goc(
                cwd, "new", "child-card",
                "--gate", "none", "--tag", "story",
                "--advances", "parent-card",
            ))
            status = self._git_status(cwd)
            # The default leaves the new card untracked AND the parent
            # README as modified — both must be present for the option C
            # contract to hold.
            self.assertIn("child-card", status)
            self.assertIn("parent-card/README.md", status)

    def test_new_commit_and_no_commit_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            result = self.run_goc(
                cwd, "new", "card-x",
                "--gate", "none", "--tag", "story",
                "--commit", "--no-commit",
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("pass only one of --commit / --no-commit", result.stderr)
            # The flag conflict aborts BEFORE any disk write — no card dir
            # is left behind.
            self.assertFalse((cwd / ".game-of-cards" / "deck" / "card-x").exists())


if __name__ == "__main__":
    unittest.main()
