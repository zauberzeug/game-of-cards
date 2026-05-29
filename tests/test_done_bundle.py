from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DoneBundleTest(unittest.TestCase):
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

    def write_card(self, cwd: Path, title: str, *, dod_open: int = 0) -> None:
        boxes = "\n".join(
            f"  - [{'x' if i >= dod_open else ' '}] item-{i}" for i in range(2)
        )
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
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
            f"{boxes}\n"
            "---\n\n"
            f"# {title}\n"
        )
        (card_dir / "log.md").write_text("")

    def test_bundle_closes_multiple_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "card-a")
            self.write_card(cwd, "card-b")

            result = self.run_goc(cwd, "done", "--bundle", "card-a", "card-b")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("card-a: active → done", result.stdout)
            self.assertIn("card-b: active → done", result.stdout)
            self.assertIn("Bundled close: 2 cards", result.stdout)

            log_a = (cwd / "deck" / "card-a" / "log.md").read_text()
            log_b = (cwd / "deck" / "card-b" / "log.md").read_text()
            self.assertIn("Closure verification", log_a)
            self.assertIn("bundled", log_a)
            self.assertIn("Bundled with**: card-b", log_a)
            self.assertIn("Bundled with**: card-a", log_b)

            readme_a = (cwd / "deck" / "card-a" / "README.md").read_text()
            self.assertIn("status: done", readme_a)
            self.assertNotIn("closed_at: null", readme_a)

    def test_bundle_refuses_unchecked_dod(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "good-card")
            self.write_card(cwd, "bad-card", dod_open=1)

            result = self.run_goc(cwd, "done", "--bundle", "good-card", "bad-card")
            self.assertEqual(2, result.returncode)
            self.assertIn("bad-card", result.stderr)
            self.assertIn("unchecked DoD boxes", result.stderr)

            readme_good = (cwd / "deck" / "good-card" / "README.md").read_text()
            self.assertIn("status: active", readme_good)
            self.assertEqual("", (cwd / "deck" / "good-card" / "log.md").read_text())

    def test_bundle_requires_at_least_two_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "card-a")

            result = self.run_goc(cwd, "done", "--bundle", "card-a")
            self.assertEqual(2, result.returncode)
            self.assertIn("at least 2 titles", result.stderr)

    def test_bundle_rejects_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "card-a")

            result = self.run_goc(cwd, "done", "--bundle", "card-a", "card-a")
            self.assertEqual(2, result.returncode)
            self.assertIn("duplicate", result.stderr)


if __name__ == "__main__":
    unittest.main()
