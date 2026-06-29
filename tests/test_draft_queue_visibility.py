"""Regression: draft cards are hidden from the queue but visible under --all.

Part of the placeholder-cards-superseded-before-they-are-authored fix (B): an
unauthored scaffold must not appear as queueable work, but must remain
discoverable via `--status all` and carry a `draft` flag in JSON output.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DraftQueueVisibilityTest(unittest.TestCase):
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

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode, 0, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )

    def titles(self, cwd: Path, *args: str) -> set[str]:
        result = self.run_goc(cwd, "--json", *args)
        self.assert_ok(result)
        return {c["title"] for c in json.loads(result.stdout)}

    def by_title(self, cwd: Path, *args: str) -> dict[str, dict]:
        result = self.run_goc(cwd, "--json", *args)
        self.assert_ok(result)
        return {c["title"]: c for c in json.loads(result.stdout)}

    def setup_deck(self, cwd: Path) -> None:
        # one draft (fresh scaffold) + one authored/published card
        self.assert_ok(self.run_goc(cwd, "new", "draft-card", "--gate", "none", "--tag", "story"))
        self.assert_ok(self.run_goc(cwd, "new", "live-card", "--gate", "none", "--tag", "story"))
        path = cwd / ".game-of-cards" / "deck" / "live-card" / "README.md"
        text = path.read_text()
        text = text.replace(
            "- [ ] (replace with real criteria)", "- [x] MECHANICAL: done"
        ).replace("(write the design doc here)", "Body.")
        path.write_text(text)
        self.assert_ok(self.run_goc(cwd, "publish", "live-card", "--no-commit"))

    def test_default_queue_hides_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.setup_deck(cwd)
            titles = self.titles(cwd)
            self.assertIn("live-card", titles)
            self.assertNotIn("draft-card", titles)

    def test_status_all_shows_draft_with_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.setup_deck(cwd)
            cards = self.by_title(cwd, "--status", "all")
            self.assertIn("draft-card", cards)
            self.assertTrue(cards["draft-card"]["draft"])
            self.assertFalse(cards["live-card"]["draft"])

    def test_draft_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.setup_deck(cwd)
            cards = self.by_title(cwd, "--status", "all")
            # `ready` must be False for the draft, True for the live card.
            self.assertFalse(cards["draft-card"]["ready"])
            self.assertTrue(cards["live-card"]["ready"])

    def test_board_marks_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.setup_deck(cwd)
            result = self.run_goc(cwd, "--board", "--no-color")
            self.assert_ok(result)
            # The draft carries the ✎ marker on the board.
            line = next((ln for ln in result.stdout.splitlines() if "draft-card" in ln), "")
            self.assertIn("✎", line, msg=f"board:\n{result.stdout}")


if __name__ == "__main__":
    unittest.main()
