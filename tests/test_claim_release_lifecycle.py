"""Claim lifecycle invariants: active cards have owners and releases clear them."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _card_text(*, status: str, worker: str | None = None) -> str:
    worker_line = f"worker: {worker}\n" if worker is not None else ""
    return (
        "---\n"
        "title: claim-probe\n"
        "summary: Claim lifecycle regression probe.\n"
        f"status: {status}\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-08-25\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] TDD: lifecycle invariant holds\n"
        f"{worker_line}"
        "---\n\n"
        "# Claim probe\n"
    )


class ClaimReleaseLifecycleTest(unittest.TestCase):
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

    def make_deck(self, tmp: str, *, status: str, worker: str | None = None) -> Path:
        root = Path(tmp)
        card_dir = root / ".game-of-cards" / "deck" / "claim-probe"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(_card_text(status=status, worker=worker))
        return card_dir / "README.md"

    def test_validate_rejects_active_card_without_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.make_deck(tmp, status="active")

            result = self.run_goc(Path(tmp), "validate")

            self.assertNotEqual(0, result.returncode)
            self.assertIn(
                "claim-probe: worker: must be set when status=active",
                result.stdout + result.stderr,
            )

    def test_status_open_clears_live_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(
                tmp, status="active", worker="{who: alice, where: feature/probe}"
            )

            result = self.run_goc(
                Path(tmp), "status", "claim-probe", "open", "--no-commit"
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("status: open", text)
            self.assertNotIn("worker:", text)

    def test_setting_wait_releases_active_claim_and_keeps_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(
                tmp, status="active", worker="{who: alice, where: feature/probe}"
            )

            result = self.run_goc(
                Path(tmp), "wait", "claim-probe", "--reason", "external", "--no-commit"
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("active claim released to open", result.stdout)
            text = readme.read_text()
            self.assertIn("status: open", text)
            self.assertIn("waiting_on: external", text)
            self.assertNotIn("worker:", text)


if __name__ == "__main__":
    unittest.main()
