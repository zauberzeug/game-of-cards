from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_done_card(cwd: Path, title: str, created: str, closed_at: str) -> None:
    card_dir = cwd / ".game-of-cards" / "deck" / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f'summary: "ordering check fixture"\n'
        "status: done\n"
        "stage: null\n"
        "contribution: low\n"
        f"created: {created}\n"
        f"closed_at: {closed_at}\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [x] PROCESS: test card\n"
        "---\n\n"
        f"# {title}\n"
    )
    (card_dir / "log.md").write_text("")


def _write_open_card(cwd: Path, title: str, created: str) -> None:
    card_dir = cwd / ".game-of-cards" / "deck" / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f'summary: "shape fixture"\n'
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        f"created: {created}\n"
        "closed_at: null\n"
        "human_gate: none\n"
        "advances: []\n"
        "advanced_by: []\n"
        "tags: [bug]\n"
        "definition_of_done: |\n"
        "  - [ ] PROCESS: test card\n"
        "---\n\n"
        f"# {title}\n"
    )
    (card_dir / "log.md").write_text("")


def _run_validate(cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", "validate", "--quiet"],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class ValidateClosedAtOrderingTest(unittest.TestCase):
    def test_closed_at_before_created_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(cwd, "closed-before-created", "2026-06-15", "2026-01-01")

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("closed-before-created: closed_at:", result.stderr)
            self.assertIn("predates created", result.stderr)

    def test_intra_day_datetime_inversion_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(
                cwd,
                "intraday-inversion",
                "2026-06-15T12:00:00Z",
                "2026-06-15T08:00:00Z",
            )

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("intraday-inversion: closed_at:", result.stderr)
            self.assertIn("predates created", result.stderr)

    def test_closed_at_equals_created_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(cwd, "closed-equals-created", "2026-06-15", "2026-06-15")

            result = _run_validate(cwd)

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")

    def test_closed_at_after_created_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(cwd, "closed-after-created", "2026-01-01", "2026-06-15")

            result = _run_validate(cwd)

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")

    def test_same_day_datetime_created_bare_date_closed_accepted(self) -> None:
        # Day-granularity `closed_at` on a card created at a sub-day datetime
        # the same calendar day is coherent — the bare date must not be
        # promoted to midnight and then flagged as predating `created`.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(
                cwd,
                "same-day-dt-created-bare-closed",
                '"2026-06-15T20:00:00Z"',
                "2026-06-15",
            )

            result = _run_validate(cwd)

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")

    def test_same_day_bare_date_created_datetime_closed_accepted(self) -> None:
        # The inverse mix (date created, same-day datetime closed) must also
        # stay clean.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(
                cwd,
                "same-day-bare-created-dt-closed",
                "2026-06-15",
                '"2026-06-15T20:00:00Z"',
            )

            result = _run_validate(cwd)

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")

    def test_bare_date_closed_earlier_day_than_datetime_created_rejected(self) -> None:
        # A bare-date `closed_at` on a strictly-earlier calendar day than a
        # datetime `created` is a genuine inversion and must still fire.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_done_card(
                cwd,
                "bare-closed-earlier-day",
                '"2026-06-15T20:00:00Z"',
                "2026-06-14",
            )

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("bare-closed-earlier-day: closed_at:", result.stderr)
            self.assertIn("predates created", result.stderr)

    def test_non_iso_created_still_only_shape_error_no_crash(self) -> None:
        # A malformed `created` must surface the existing shape error and must
        # NOT crash the new ordering comparison (which skips when a parse fails).
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_open_card(cwd, "bad-created-shape", "not-a-date")

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn("bad-created-shape: created:", result.stderr)
            self.assertNotIn("predates created", result.stderr)


if __name__ == "__main__":
    unittest.main()
