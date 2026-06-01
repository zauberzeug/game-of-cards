from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepairEdgesTest(unittest.TestCase):
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

    def readme_path(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title / "README.md"

    def readme(self, cwd: Path, title: str) -> str:
        return self.readme_path(cwd, title).read_text()

    def write_readme(self, cwd: Path, title: str, text: str) -> None:
        self.readme_path(cwd, title).write_text(text)

    def new_card(self, cwd: Path, title: str) -> None:
        self.assert_goc_ok(self.run_goc(cwd, "new", title, "--gate", "none", "--tag", "story"))

    def dirty_parent_advances_child_half_edge(self, cwd: Path) -> None:
        self.new_card(cwd, "parent-card")
        self.new_card(cwd, "child-card")
        self.assert_goc_ok(self.run_goc(cwd, "advance", "child-card", "--by", "parent-card", "--no-commit"))
        self.write_readme(
            cwd,
            "child-card",
            self.readme(cwd, "child-card").replace(
                "advanced_by:\n  - parent-card\n",
                "advanced_by: []\n",
            ),
        )

    def test_repair_edges_dry_run_reports_diff_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.dirty_parent_advances_child_half_edge(cwd)

            result = self.run_goc(cwd, "repair-edges")

            self.assert_goc_ok(result)
            self.assertIn("Half-edges that would be repaired (1):", result.stdout)
            self.assertIn(
                "parent-card: advances contains 'child-card' but child-card.advanced_by is missing 'parent-card'",
                result.stdout,
            )
            self.assertIn("-advanced_by: []", result.stdout)
            self.assertIn("+advanced_by:", result.stdout)
            self.assertIn("+  - parent-card", result.stdout)
            self.assertIn("advanced_by: []", self.readme(cwd, "child-card"))

    def test_repair_edges_apply_repairs_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.dirty_parent_advances_child_half_edge(cwd)

            result = self.run_goc(cwd, "repair-edges", "--apply")

            self.assert_goc_ok(result)
            self.assertIn("Repaired 1 half-edge(s).", result.stdout)
            self.assertIn("advanced_by:\n  - parent-card\n", self.readme(cwd, "child-card"))
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

            second = self.run_goc(cwd, "repair-edges", "--apply")

            self.assert_goc_ok(second)
            self.assertIn("No half-edges found.", second.stdout)

    def test_repair_edges_refuses_cycle_creating_reverse_edge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for title in ("a-card", "b-card", "c-card"):
                self.new_card(cwd, title)
            self.assert_goc_ok(self.run_goc(cwd, "advance", "b-card", "--by", "a-card", "--no-commit"))
            self.assert_goc_ok(self.run_goc(cwd, "advance", "c-card", "--by", "b-card", "--no-commit"))
            self.write_readme(
                cwd,
                "c-card",
                self.readme(cwd, "c-card").replace(
                    "advances: []\n",
                    "advances:\n  - a-card\n",
                ),
            )

            result = self.run_goc(cwd, "repair-edges", "--apply")

            self.assertEqual(1, result.returncode, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}")
            self.assertIn("Structural problems requiring human review:", result.stderr)
            self.assertIn("c-card \u2192 a-card would create a cycle in the advances graph", result.stderr)
            self.assertNotIn("c-card", self.readme(cwd, "a-card"))

    def test_repair_edges_help_names_both_relation_classes(self) -> None:
        import argparse

        from goc.engine import _build_parser, _cmd_repair_edges, find_half_edges

        # The subparser help= string (rendered into `goc --help`'s subcommand
        # listing) must name both relation classes so a user seeing
        # validate's "Run 'goc repair-edges --apply' to fix." against a
        # supersession half-edge can tell the verb covers their case.
        parser = _build_parser()
        subparsers_action = next(
            a for a in parser._actions
            if isinstance(a, argparse._SubParsersAction)
        )
        repair_help_text = next(
            ca.help for ca in subparsers_action._choices_actions
            if ca.dest == "repair-edges"
        )
        self.assertIn("supersedes", repair_help_text)
        self.assertIn("advances", repair_help_text)

        # Same coverage assertion against the function docstrings: future
        # readers of the source must see the full scope, not just the
        # advances/advanced_by half.
        self.assertIn("supersedes", _cmd_repair_edges.__doc__ or "")
        self.assertIn("supersedes", find_half_edges.__doc__ or "")

    def test_validate_suggests_repair_edges_for_half_edge_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.dirty_parent_advances_child_half_edge(cwd)

            result = self.run_goc(cwd, "validate", "--quiet")

            self.assertEqual(1, result.returncode)
            self.assertIn("(half-edge)", result.stderr)
            self.assertTrue(result.stderr.rstrip().endswith("Run 'goc repair-edges --apply' to fix."))


if __name__ == "__main__":
    unittest.main()
