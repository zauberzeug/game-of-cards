from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine


class AttestAutomatedTimeoutTest(unittest.TestCase):
    """Automated attestation checks accept a positive integer timeout.

    Existing configs keep the historical 300-second budget. Invalid values
    fail as check results before spawning a command, so a configuration typo
    cannot become either a traceback or an accidentally unbounded process.
    """

    def test_configured_timeout_is_forwarded_and_reported_on_expiry(self) -> None:
        check = {
            "name": "repository-check",
            "kind": "automated",
            "cmd": ["make", "check"],
            "timeout_seconds": 1000,
        }
        expired = subprocess.TimeoutExpired(cmd=check["cmd"], timeout=1000)

        with mock.patch.object(engine.subprocess, "run", side_effect=expired) as run:
            result = engine._run_automated_check(check)

        self.assertEqual((False, "TIMEOUT (>1000s)"), result)
        run.assert_called_once_with(
            check["cmd"],
            capture_output=True,
            text=True,
            timeout=1000,
            cwd=str(engine.REPO_ROOT),
            check=False,
        )

    def test_absent_timeout_uses_existing_300_second_default(self) -> None:
        check = {
            "name": "repository-check",
            "kind": "automated",
            "cmd": ["make", "check"],
        }
        expired = subprocess.TimeoutExpired(cmd=check["cmd"], timeout=300)

        with mock.patch.object(engine.subprocess, "run", side_effect=expired) as run:
            result = engine._run_automated_check(check)

        self.assertEqual((False, "TIMEOUT (>300s)"), result)
        self.assertEqual(300, run.call_args.kwargs["timeout"])

    def test_invalid_timeout_fails_without_spawning_command(self) -> None:
        invalid_values = (True, False, "1000", 0.5, 0, -1, 10**300)

        for value in invalid_values:
            with (
                self.subTest(timeout_seconds=value),
                mock.patch.object(engine.subprocess, "run") as run,
            ):
                passed, summary = engine._run_automated_check(
                    {
                        "name": "repository-check",
                        "kind": "automated",
                        "cmd": ["make", "check"],
                        "timeout_seconds": value,
                    }
                )

                self.assertFalse(passed)
                self.assertIn("invalid timeout_seconds", summary)
                self.assertIn("positive integer", summary)
                run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
