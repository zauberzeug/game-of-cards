from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ActiveNoticeWorkerScopeTest(unittest.TestCase):
    """The `ACTIVE:` heads-up banner must honor `--worker`, mirroring the
    board path. Regression for active-card-banner-ignores-worker-filter."""

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

    def write_card(self, cwd: Path, title: str, status: str, worker: str) -> None:
        card_dir = cwd / "deck" / title
        card_dir.mkdir(parents=True)
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
            f"worker: {worker}\n"
            "definition_of_done: |\n"
            "  - [ ] test card\n"
            "---\n\n"
            f"# {title}\n"
        )

    def _banner(self, stdout: str) -> str:
        return next((ln for ln in stdout.splitlines() if ln.startswith("ACTIVE:")), "")

    def _make_deck(self, cwd: Path) -> None:
        self.write_card(cwd, "alice-active", "active", "alice")
        self.write_card(cwd, "bob-active", "active", "bob")
        self.write_card(cwd, "alice-open", "open", "alice")

    def test_worker_filter_scopes_active_banner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_deck(cwd)

            result = self.run_goc(cwd, "--worker", "alice")

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            banner = self._banner(result.stdout)
            self.assertIn("alice-active", banner)
            self.assertNotIn("bob-active", banner)

    def test_unfiltered_banner_lists_all_active_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self._make_deck(cwd)

            result = self.run_goc(cwd)

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            banner = self._banner(result.stdout)
            self.assertIn("alice-active", banner)
            self.assertIn("bob-active", banner)


if __name__ == "__main__":
    unittest.main()
