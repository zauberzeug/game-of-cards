from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SinceFilterTest(unittest.TestCase):
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

    def write_done_card(self, cwd: Path, title: str, closed_at: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: done\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-01\n"
            f"closed_at: {closed_at}\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [x] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_invalid_since_rejects_non_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "--done", "--since", "nope")

            combined = result.stdout + result.stderr
            self.assertEqual(2, result.returncode, msg=combined)
            self.assertIn("--since", result.stderr)
            self.assertNotIn("Traceback", combined)

    def test_valid_since_filters_done_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_done_card(cwd, "old-card", "2026-05-01")
            self.write_done_card(cwd, "recent-card", "2026-05-04")

            result = self.run_goc(cwd, "--done", "--since", "2026-05-03")

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("recent-card", result.stdout)
            self.assertNotIn("old-card", result.stdout)


if __name__ == "__main__":
    unittest.main()
