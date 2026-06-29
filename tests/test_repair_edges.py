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

    def test_repair_edges_dry_run_exits_nonzero_on_structural_half_edge(self) -> None:
        # Regression: the read-only preview must signal the same non-zero exit
        # on an unfixable structural half-edge that --apply does, so a CI gate
        # or &&-chained script using the safe preview does not silently pass a
        # deck carrying half-edges no verb can repair.
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

            dry = self.run_goc(cwd, "repair-edges")

            self.assertEqual(
                1, dry.returncode, msg=f"stdout:\n{dry.stdout}\nstderr:\n{dry.stderr}"
            )
            self.assertIn("Structural problems requiring human review:", dry.stderr)
            self.assertIn("Dry run", dry.stdout)
            # Dry-run must NOT mutate the deck despite the non-zero exit.
            self.assertNotIn("c-card", self.readme(cwd, "a-card"))

    def interacting_advances_half_edges(self, cwd: Path) -> None:
        """Two Type-β advances half-edges that form a cycle once both reverse
        halves are added: each card's advanced_by names the other, but neither
        carries the matching advances entry. Repairing the first adds the
        advances forward edge that makes the second structural."""
        for title, other in (("card-a", "card-b"), ("card-b", "card-a")):
            self.new_card(cwd, title)
            self.write_readme(
                cwd,
                title,
                self.readme(cwd, title).replace(
                    "advanced_by: []\n",
                    f"advanced_by:\n  - {other}\n",
                ),
            )

    def test_repair_edges_dry_run_matches_apply_on_interacting_half_edges(self) -> None:
        # Regression: the dry-run classification must simulate earlier same-run
        # repairs the way --apply does, so the preview's "would be repaired (N)"
        # set equals the set --apply actually repairs. Before the fix the dry
        # run classified every edge against one original snapshot and promised 2
        # repairs while --apply (reloading before each edge) performed 1.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.interacting_advances_half_edges(cwd)

            dry = self.run_goc(cwd, "repair-edges")
            # Parity with --apply extends to the exit code: a structural
            # half-edge is a hard failure even when some edges are fixable, so
            # the read-only preview exits non-zero just as --apply does below.
            self.assertEqual(
                1, dry.returncode, msg=f"stdout:\n{dry.stdout}\nstderr:\n{dry.stderr}"
            )
            self.assertIn("Half-edges that would be repaired (1):", dry.stdout)
            # The structural edge is surfaced in the preview too (to stderr),
            # not silently folded into the fixable count.
            self.assertIn("would create a cycle in the advances graph", dry.stderr)

            apply = self.run_goc(cwd, "repair-edges", "--apply")
            self.assertEqual(
                1, apply.returncode, msg=f"stdout:\n{apply.stdout}\nstderr:\n{apply.stderr}"
            )
            apply_repaired = apply.stdout.count("repaired: ")
            self.assertEqual(
                1,
                apply_repaired,
                msg=f"dry-run promised 1 repair; apply performed {apply_repaired}",
            )
            self.assertIn("would create a cycle in the advances graph", apply.stderr)

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

    def test_migrate_list_style_help_names_all_relation_fields(self) -> None:
        import argparse

        from goc.engine import (
            _build_parser,
            _cmd_migrate_list_style,
            emit_frontmatter,
        )

        # The `migrate-list-style` subparser help= (rendered into
        # `goc --help`'s subcommand listing) and the `_cmd_migrate_list_style`
        # docstring describe the verb's *scope*. The underlying behavior
        # block-styles every member of `_BLOCK_LIST_FIELDS` (i.e. supersedes /
        # superseded_by alongside advances / advanced_by), so the scope strings
        # must name supersedes too — otherwise readers think the verb skips
        # supersession edges. Same drift class as
        # `test_repair_edges_help_names_both_relation_classes`.
        parser = _build_parser()
        subparsers_action = next(
            a for a in parser._actions
            if isinstance(a, argparse._SubParsersAction)
        )
        mls_help_text = next(
            ca.help for ca in subparsers_action._choices_actions
            if ca.dest == "migrate-list-style"
        )
        self.assertIn("supersedes", mls_help_text)
        self.assertIn("advances", mls_help_text)

        self.assertIn("supersedes", _cmd_migrate_list_style.__doc__ or "")
        self.assertIn("supersedes", emit_frontmatter.__doc__ or "")

    def test_migrate_list_style_noop_message_names_all_relation_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.assert_goc_ok(self.run_goc(cwd, "install"))
            # No cards exist, but the no-op codepath is also reached when every
            # card is already block-styled — `new` emits block style by default.
            self.new_card(cwd, "solo-card")

            result = self.run_goc(cwd, "migrate-list-style")

            self.assert_goc_ok(result)
            self.assertIn("supersedes", result.stdout)
            self.assertIn("advances", result.stdout)

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
