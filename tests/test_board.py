from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BoardRenderingTest(unittest.TestCase):
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
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_board_renders_every_status_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            for status in ("open", "active", "blocked", "done", "disproved", "superseded"):
                self.write_card(cwd, f"{status}-card", status)

            result = self.run_goc(cwd, "--board", "--no-color")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            for header in ("OPEN", "ACTIVE", "BLOCKED", "DONE", "DISPROVED", "SUPERSEDED"):
                self.assertIn(header, result.stdout)
            for status in ("open", "active", "blocked", "done", "disproved", "superseded"):
                self.assertIn(f"{status}-card", result.stdout)

    def test_board_rejects_negative_max_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "open-card", "open")

            negative = self.run_goc(cwd, "--board", "--max-rows", "-1")
            zero = self.run_goc(cwd, "--board", "--max-rows", "0")
            one = self.run_goc(cwd, "--board", "--max-rows", "1")

            self.assertEqual(2, negative.returncode, msg=negative.stdout + negative.stderr)
            self.assertIn("Invalid value for '--max-rows'", negative.stderr)
            self.assertEqual(0, zero.returncode, msg=zero.stderr)
            self.assertEqual(0, one.returncode, msg=one.stderr)


if __name__ == "__main__":
    unittest.main()
