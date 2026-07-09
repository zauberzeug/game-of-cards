"""Title arguments must resolve strictly inside DECK_DIR.

`DECK_DIR / title` with a path-shaped title escapes the deck: joining an
absolute path replaces DECK_DIR entirely, and a `../` component walks out
of the tree. Every verb that resolves an existing card's title must refuse
such titles with exit 2 *before* any read or write — covered here for one
read verb (show), one overlay verb (wait), and one closure verb (done),
plus the move source path.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUTSIDE_CARD = """---
title: outside-card
status: active
stage: null
contribution: low
created: 2026-05-01
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] item-0
---

# outside-card
"""


class TitleResolutionContainmentTest(unittest.TestCase):
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

    def make_repo(self, tmp: str) -> tuple[Path, Path]:
        """Return (repo_cwd, outside_card_dir) — the outside card lives next
        to the repo so both an absolute path and `../../outside-card`
        (relative to DECK_DIR) reach it."""
        base = Path(tmp)
        cwd = base / "repo"
        card_dir = cwd / "deck" / "real-card"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            "title: real-card\n"
            "summary: real-card\n"
            "status: active\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-01\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] item-0\n"
            "---\n\n"
            "# real-card\n"
        )
        (card_dir / "log.md").write_text("")
        outside = base / "outside-card"
        outside.mkdir()
        (outside / "README.md").write_text(OUTSIDE_CARD)
        return cwd, outside

    def assert_refused(self, result: subprocess.CompletedProcess[str], title: str) -> None:
        self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
        self.assertIn("invalid card title", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("outside-card", result.stdout)

    def escape_titles(self, outside: Path) -> list[str]:
        return [str(outside), "../../outside-card"]

    def test_show_refuses_path_shaped_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            for title in self.escape_titles(outside):
                result = self.run_goc(cwd, "show", title)
                self.assert_refused(result, title)

    def test_wait_refuses_path_shaped_titles_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            for title in self.escape_titles(outside):
                result = self.run_goc(cwd, "wait", title, "--reason", "external")
                self.assert_refused(result, title)
                self.assertNotIn("waiting_on", (outside / "README.md").read_text())

    def test_done_refuses_path_shaped_titles_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            for title in self.escape_titles(outside):
                result = self.run_goc(cwd, "done", title)
                self.assert_refused(result, title)
                self.assertIn("status: active", (outside / "README.md").read_text())

    def test_move_refuses_path_shaped_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, outside = self.make_repo(tmp)
            result = self.run_goc(cwd, "move", str(outside), "captured-card")
            self.assert_refused(result, str(outside))
            self.assertTrue(outside.exists())
            self.assertFalse((cwd / "deck" / "captured-card").exists())

    def test_bare_titles_still_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd, _outside = self.make_repo(tmp)
            result = self.run_goc(cwd, "show", "real-card")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("# real-card", result.stdout)

            result = self.run_goc(cwd, "wait", "real-card", "--reason", "external", "--no-commit")
            self.assertEqual(0, result.returncode, msg=result.stderr)

            result = self.run_goc(cwd, "done", "real-card")
            self.assertEqual(0, result.returncode, msg=result.stderr)


if __name__ == "__main__":
    unittest.main()
