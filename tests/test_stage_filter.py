from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StageFilterTest(unittest.TestCase):
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

    def write_card(self, cwd: Path, title: str, stage: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            f"stage: {stage}\n"
            "contribution: medium\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_invalid_stage_range_rejects_unknown_stages_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "--stage", "foo-bar")

            combined = f"{result.stdout}\n{result.stderr}"
            self.assertEqual(2, result.returncode, msg=combined)
            self.assertIn("--stage", result.stderr)
            self.assertNotIn("Traceback", combined)
            self.assertNotIn("ValueError", combined)

    def test_valid_stage_values_and_ranges_still_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "alpha-card", "alpha")
            self.write_card(cwd, "beta-card", "beta")
            self.write_card(cwd, "stable-card", "stable")

            alpha = self.run_goc(cwd, "--stage", "alpha")
            reverse_range = self.run_goc(cwd, "--stage", "stable-alpha")

            self.assertEqual(0, alpha.returncode, msg=alpha.stderr)
            self.assertIn("alpha-card", alpha.stdout)
            self.assertNotIn("beta-card", alpha.stdout)
            self.assertEqual(0, reverse_range.returncode, msg=reverse_range.stderr)
            self.assertIn("alpha-card", reverse_range.stdout)
            self.assertIn("beta-card", reverse_range.stdout)
            self.assertIn("stable-card", reverse_range.stdout)


if __name__ == "__main__":
    unittest.main()
