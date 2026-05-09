from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TagFilterTest(unittest.TestCase):
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

    def write_card(self, cwd: Path, title: str, tag: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            f"tags: [{tag}]\n"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def test_invalid_tag_filter_rejects_unknown_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_goc(cwd, "--tag", "not-a-real-tag")

            combined = result.stdout + result.stderr
            self.assertEqual(2, result.returncode, msg=combined)
            self.assertIn("unknown tag 'not-a-real-tag'", result.stderr)
            self.assertNotIn("Traceback", combined)

    def test_builtin_and_project_extended_tag_filters_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "bug-card", "bug")
            self.write_card(cwd, "project-card", "project-tag")
            game_dir = cwd / ".game-of-cards"
            game_dir.mkdir()
            (game_dir / "canonical-tags.md").write_text(
                "```yaml\n"
                "canonical_tags:\n"
                "  - project-tag\n"
                "```\n"
            )

            bug = self.run_goc(cwd, "--tag", "bug")
            project = self.run_goc(cwd, "--tag", "project-tag")

            self.assertEqual(0, bug.returncode, msg=bug.stderr)
            self.assertIn("bug-card", bug.stdout)
            self.assertNotIn("project-card", bug.stdout)
            self.assertEqual(0, project.returncode, msg=project.stderr)
            self.assertIn("project-card", project.stdout)
            self.assertNotIn("bug-card", project.stdout)


if __name__ == "__main__":
    unittest.main()
