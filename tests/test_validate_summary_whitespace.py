from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_card(cwd: Path, title: str, summary_line: str) -> None:
    card_dir = cwd / ".game-of-cards" / "deck" / title
    card_dir.mkdir(parents=True)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"{summary_line}\n"
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-05-30\n"
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


class ValidateSummaryWhitespaceTest(unittest.TestCase):
    def test_bare_whitespace_summary_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "ws-summary-bare", 'summary: "   "')

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "ws-summary-bare: summary: must not be empty or whitespace-only",
                result.stderr,
            )

    def test_empty_summary_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "ws-summary-empty", 'summary: ""')

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "ws-summary-empty: summary: must not be empty or whitespace-only",
                result.stderr,
            )

    def test_valid_summary_still_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "ok-summary", 'summary: "real summary text"')

            result = _run_validate(cwd)

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")


if __name__ == "__main__":
    unittest.main()
