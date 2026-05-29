from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CLOSED_CARD = """\
---
title: closed-fixture
summary: "Closed fixture for terminal-status guard."
status: done
stage: null
contribution: medium
created: "2026-05-01T00:00:00Z"
closed_at: "2026-05-15T00:00:00Z"
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] one
---

# closed-fixture

Original body.
"""


class DecideTerminalStatusGuardTest(unittest.TestCase):
    """`goc decide` must refuse to record a decision on a card whose status is
    terminal (`done`, `disproved`, `superseded`), mirroring the guards in
    `_cmd_done` and `_cmd_status`. Without the guard, a closed card whose gate
    was left raised could be silently mutated — README rewritten, `human_gate`
    lowered, and the success line falsely promising the card is pullable."""

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

    def _write_card(self, cwd: Path, body: str) -> Path:
        card_dir = cwd / ".game-of-cards" / "deck" / "closed-fixture"
        card_dir.mkdir(parents=True)
        readme = card_dir / "README.md"
        readme.write_text(body)
        return card_dir

    def test_decide_refuses_done_card_and_leaves_readme_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            card_dir = self._write_card(cwd, CLOSED_CARD)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(
                cwd,
                "decide",
                "closed-fixture",
                "--decision",
                "go",
                "--because",
                "irrelevant on a closed card",
                "--no-commit",
            )

            self.assertNotEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
            )
            self.assertIn("terminal", result.stderr)
            self.assertEqual(before, readme.read_text())
            self.assertFalse((card_dir / "log.md").exists())

    def test_decide_refuses_disproved_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            body = CLOSED_CARD.replace("status: done", "status: disproved")
            card_dir = self._write_card(cwd, body)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(
                cwd,
                "decide",
                "closed-fixture",
                "--decision",
                "go",
                "--because",
                "irrelevant on a disproved card",
                "--no-commit",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, readme.read_text())

    def test_decide_refuses_superseded_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            body = CLOSED_CARD.replace("status: done", "status: superseded")
            card_dir = self._write_card(cwd, body)
            readme = card_dir / "README.md"
            before = readme.read_text()

            result = self.run_goc(
                cwd,
                "decide",
                "closed-fixture",
                "--decision",
                "go",
                "--because",
                "irrelevant on a superseded card",
                "--no-commit",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(before, readme.read_text())


if __name__ == "__main__":
    unittest.main()
