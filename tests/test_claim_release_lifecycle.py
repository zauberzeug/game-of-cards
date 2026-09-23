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
    def run_goc(
        self,
        cwd: Path,
        *args: str,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        # The claim path resolves a worker identity from the environment. Bind
        # every source explicitly so these tests never inherit the developer's
        # git identity — otherwise the identity-less case below passes on CI and
        # fails on a workstation, which is the same defect it is guarding.
        env.pop("GOC_WORKER_WHO", None)
        env.pop("GOC_WORKER_WHERE", None)
        env["GIT_CONFIG_GLOBAL"] = os.devnull
        env["GIT_CONFIG_SYSTEM"] = os.devnull
        if env_overrides:
            env.update(env_overrides)
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

    def test_claim_without_identity_fails_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")
            before = readme.read_text()

            result = self.run_goc(
                Path(tmp), "status", "claim-probe", "active", "--no-commit"
            )

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("cannot claim without a worker identity", result.stderr)
            # The refusal must land before the write: a card left on `active`
            # without a worker is exactly the shape validate now rejects, so a
            # guard that fails after mutating would create the defect it guards.
            self.assertEqual(before, readme.read_text())

    def test_env_worker_who_supplies_the_claim_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")

            result = self.run_goc(
                Path(tmp),
                "status",
                "claim-probe",
                "active",
                "--no-commit",
                env_overrides={
                    "GOC_WORKER_WHO": "sandbox-worker",
                    "GOC_WORKER_WHERE": "container:probe",
                },
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("status: active", text)
            # `where` carries a colon, so the emitter quotes it — asserting the
            # quoted form keeps this test honest about what lands on disk.
            self.assertIn('worker: {who: sandbox-worker, where: "container:probe"}', text)

    def test_explicit_worker_flag_overrides_the_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")

            result = self.run_goc(
                Path(tmp),
                "status",
                "claim-probe",
                "active",
                "--worker-who",
                "flag-worker",
                "--no-commit",
                env_overrides={"GOC_WORKER_WHO": "env-worker"},
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("flag-worker", text)
            self.assertNotIn("env-worker", text)

    def test_wait_keep_claim_preserves_the_active_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(
                tmp, status="active", worker="{who: alice, where: feature/probe}"
            )

            result = self.run_goc(
                Path(tmp),
                "wait",
                "claim-probe",
                "--reason",
                "external",
                "--keep-claim",
                "--no-commit",
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("active claim kept", result.stdout)
            text = readme.read_text()
            self.assertIn("status: active", text)
            self.assertIn("waiting_on: external", text)
            self.assertIn("who: alice", text)


if __name__ == "__main__":
    unittest.main()
