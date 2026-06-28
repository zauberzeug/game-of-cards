"""Regression: `goc --version` must work at any top-level position.

The version flag was once intercepted by a hand-rolled `argv[0]` check
in `goc.cli.main()` *before* argparse ran, and `_build_parser` never
registered a `--version` action. So `--version` was honored only as the
very first token: `goc --no-color --version` and `goc --status all
--version` fell through to the engine parser, which rejected them with
`unrecognized arguments: --version` (exit 2), and `--version` was absent
from `goc --help`.

The fix registers `--version`/`-V` as an argparse `action="version"` on
the engine main parser, so it is position-independent among the
program's own top-level options and is listed in help.
"""
from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
_VERSION_RE = re.compile(r"^goc, version \S")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "goc.cli", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


class VersionFlagPositionTest(unittest.TestCase):
    def _assert_prints_version(self, *args: str) -> None:
        result = _run(*args)
        self.assertEqual(
            result.returncode, 0,
            f"`goc {' '.join(args)}` exited {result.returncode}; "
            f"stderr={result.stderr!r}",
        )
        self.assertRegex(
            result.stdout.strip(), _VERSION_RE,
            f"`goc {' '.join(args)}` did not print the version: "
            f"stdout={result.stdout!r}",
        )

    def test_version_as_first_token(self) -> None:
        self._assert_prints_version("--version")
        self._assert_prints_version("-V")

    def test_version_after_another_global_flag(self) -> None:
        # The historically-broken shape: a global flag ahead of --version.
        self._assert_prints_version("--no-color", "--version")
        self._assert_prints_version("--status", "all", "--version")

    def test_version_listed_in_help(self) -> None:
        result = _run("--help")
        self.assertEqual(result.returncode, 0, f"stderr={result.stderr!r}")
        self.assertIn(
            "--version", result.stdout,
            "`goc --help` does not list the --version flag",
        )


if __name__ == "__main__":
    unittest.main()
