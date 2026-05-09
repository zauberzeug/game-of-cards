from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StatusFilterTest(unittest.TestCase):
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

    def write_card(self, cwd: Path, title: str, status: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        done = "x" if status == "done" else " "
        closed_at = "2026-05-04" if status == "done" else "null"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            f"closed_at: {closed_at}\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            f"  - [{done}] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_invalid_status_filter_rejects_unknown_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "--status", "bogus")

            combined = result.stdout + result.stderr
            self.assertEqual(2, result.returncode, msg=combined)
            self.assertIn("bogus", result.stderr)
            self.assertNotIn("Traceback", combined)

    def test_status_all_and_specific_filters_still_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-card", "open")
            self.write_card(cwd, "done-card", "done")

            open_only = self.run_goc(cwd, "--status", "open")
            all_cards = self.run_goc(cwd, "--status", "all")

            self.assertEqual(0, open_only.returncode, msg=open_only.stderr)
            self.assertIn("open-card", open_only.stdout)
            self.assertNotIn("done-card", open_only.stdout)
            self.assertEqual(0, all_cards.returncode, msg=all_cards.stderr)
            self.assertIn("open-card", all_cards.stdout)
            self.assertIn("done-card", all_cards.stdout)

    def test_done_shortcut_conflicts_with_explicit_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "done-card", "done")

            conflict = self.run_goc(cwd, "--done", "--status", "open")
            done_shortcut = self.run_goc(cwd, "--done")
            done_status = self.run_goc(cwd, "--status", "done")

            self.assertEqual(2, conflict.returncode, msg=conflict.stdout + conflict.stderr)
            self.assertIn("pass only one of --done / --status", conflict.stderr)
            self.assertEqual(0, done_shortcut.returncode, msg=done_shortcut.stderr)
            self.assertIn("done-card", done_shortcut.stdout)
            self.assertEqual(0, done_status.returncode, msg=done_status.stderr)
            self.assertIn("done-card", done_status.stdout)


if __name__ == "__main__":
    unittest.main()
