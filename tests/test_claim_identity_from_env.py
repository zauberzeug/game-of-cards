"""Claim identity: `goc status <title> active` always names who claimed the card.

The claim resolves `who` from `--worker-who`, else an existing designation on
the card, else `$GOC_WORKER_WHO`, else `git config user.name` — and refuses,
before writing, when none of them yields an identity.
"""

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
        "summary: Claim identity regression probe.\n"
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
        "  - [ ] TDD: claim identity invariant holds\n"
        f"{worker_line}"
        "---\n\n"
        "# Claim probe\n"
    )


class ClaimIdentityFromEnvTest(unittest.TestCase):
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
        card_dir = Path(tmp) / ".game-of-cards" / "deck" / "claim-probe"
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(_card_text(status=status, worker=worker))
        return card_dir / "README.md"

    def claim(self, tmp: str, *extra: str, env_overrides: dict[str, str] | None = None):
        return self.run_goc(
            Path(tmp), "status", "claim-probe", "active", *extra, "--no-commit",
            env_overrides=env_overrides,
        )

    def test_claim_without_identity_fails_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")
            before = readme.read_text()

            result = self.claim(tmp)

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("cannot claim without a worker identity", result.stderr)
            # The refusal names both remedies: the flag for a one-off claim, the
            # variable for a container that never has a git identity.
            self.assertIn("--worker-who", result.stderr)
            self.assertIn("GOC_WORKER_WHO", result.stderr)
            # The refusal must land before the write: a card left `active`
            # without a worker is the unattributable claim the guard prevents.
            self.assertEqual(before, readme.read_text())

    def test_blank_env_worker_who_counts_as_unset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")
            before = readme.read_text()

            result = self.claim(tmp, env_overrides={"GOC_WORKER_WHO": "   "})

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("cannot claim without a worker identity", result.stderr)
            self.assertEqual(before, readme.read_text())

    def test_env_worker_who_supplies_the_claim_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")

            result = self.claim(
                tmp,
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

            result = self.claim(
                tmp, "--worker-who", "flag-worker",
                env_overrides={"GOC_WORKER_WHO": "env-worker"},
            )

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("flag-worker", text)
            self.assertNotIn("env-worker", text)

    def test_existing_designation_wins_over_the_environment(self) -> None:
        # A card pre-assigned to a worker (`worker: gpu-required`) keeps that
        # designation when claimed; the environment only fills an empty slot.
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open", worker="gpu-required")

            result = self.claim(tmp, env_overrides={"GOC_WORKER_WHO": "env-worker"})

            self.assertEqual(0, result.returncode, msg=result.stdout + result.stderr)
            text = readme.read_text()
            self.assertIn("gpu-required", text)
            self.assertNotIn("env-worker", text)

    def test_env_worker_who_with_a_line_break_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readme = self.make_deck(tmp, status="open")
            before = readme.read_text()

            result = self.claim(tmp, env_overrides={"GOC_WORKER_WHO": "two\nlines"})

            self.assertEqual(2, result.returncode, msg=result.stdout + result.stderr)
            self.assertIn("GOC_WORKER_WHO must not contain a line break", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(before, readme.read_text())


if __name__ == "__main__":
    unittest.main()
