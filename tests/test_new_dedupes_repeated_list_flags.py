"""Regression guard: `goc new` writes a repeated list-flag value once.

`goc new` passed `--advances` / `--advanced-by` through
`_unique_preserving_order` but wrote `--tag` verbatim, so
`--tag bug --tag bug` landed `tags: [bug, bug]` on disk and `goc validate`
stayed green (card goc-new-writes-duplicate-tags-when-tag-flag-is-repeated).

Two of the three repeatable flags were deduplicated and the third was not,
so the tripwire below enumerates every repeatable option on the `new`
subparser: a repeatable flag added later fails the build until it is listed
in `REPEATABLE_NEW_FLAGS`, whose behavior test then holds it to the dedupe.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


# Every repeatable option on `goc new`, mapped to the frontmatter field it
# writes and a value the fixture deck accepts for it.
REPEATABLE_NEW_FLAGS = {
    "--tag": ("tags", "bug"),
    "--advances": ("advances", "target-card"),
    "--advanced-by": ("advanced_by", "parent-card"),
}


class NewDedupesRepeatedListFlagsTest(unittest.TestCase):
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

    def make_deck(self, tmp: str) -> Path:
        cwd = Path(tmp)
        (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
        return cwd

    def frontmatter(self, cwd: Path, title: str) -> dict:
        text = (cwd / ".game-of-cards" / "deck" / title / "README.md").read_text()
        fm, _ = engine.parse_frontmatter(text)
        return fm

    def test_repeated_tag_is_written_once_in_first_seen_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp)
            self.assert_goc_ok(self.run_goc(
                cwd, "new", "repeated-tag-card", "--gate", "none",
                "--tag", "bug", "--tag", "bug", "--tag", "documentation", "--tag", "bug",
            ))

            self.assertEqual(["bug", "documentation"], self.frontmatter(cwd, "repeated-tag-card")["tags"])
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_repeated_global_tag_is_written_once(self) -> None:
        # `new --tag` defaults to SUPPRESS so the global `--tag` list flows
        # into `_cmd_new` when the subcommand flag is absent — the same
        # dedupe has to cover that path too.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp)
            self.assert_goc_ok(self.run_goc(
                cwd, "--tag", "bug", "--tag", "bug", "new", "global-tag-card", "--gate", "none",
            ))

            self.assertEqual(["bug"], self.frontmatter(cwd, "global-tag-card")["tags"])

    def test_every_repeatable_flag_writes_a_repeated_value_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = self.make_deck(tmp)
            for title in ("target-card", "parent-card"):
                self.assert_goc_ok(self.run_goc(cwd, "new", title, "--gate", "none", "--tag", "story"))
            argv = ["new", "repeated-flags-card", "--gate", "none"]
            for flag, (_field, value) in REPEATABLE_NEW_FLAGS.items():
                argv += [flag, value, flag, value]

            self.assert_goc_ok(self.run_goc(cwd, *argv))

            fm = self.frontmatter(cwd, "repeated-flags-card")
            for flag, (field, value) in REPEATABLE_NEW_FLAGS.items():
                with self.subTest(flag=flag):
                    self.assertEqual([value], fm[field])
            self.assert_goc_ok(self.run_goc(cwd, "validate", "--quiet"))

    def test_table_lists_every_repeatable_flag_on_new(self) -> None:
        parser = engine._build_parser()
        subparsers = next(
            action for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        )
        repeatable = {
            max(action.option_strings, key=len)
            for action in subparsers.choices["new"]._actions
            if isinstance(action, argparse._AppendAction)
        }
        self.assertEqual(
            set(REPEATABLE_NEW_FLAGS),
            repeatable,
            msg=(
                "The repeatable options on `goc new` no longer match "
                "REPEATABLE_NEW_FLAGS. Add a new one to the table (and dedupe "
                "it in `_cmd_new` with `_unique_preserving_order`) or drop a "
                "removed one."
            ),
        )


if __name__ == "__main__":
    unittest.main()
