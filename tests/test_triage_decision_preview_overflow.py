from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DECISION_LINES = [
    "Option A: keep the cap at six lines.",
    "Option B: render the whole section.",
    "Option C: cap but advertise the overflow.",
    "Constraint 1: matches the board idiom.",
    "Constraint 2: the JSON path keeps full text.",
    "Constraint 3: readers act on this cold.",
    "LINE SEVEN MUST NOT VANISH SILENTLY.",
    "LINE EIGHT MUST NOT VANISH SILENTLY.",
]


class TriageDecisionPreviewOverflowTest(unittest.TestCase):
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

    def write_parked_card(self, cwd: Path, title: str, decision_lines: list[str]) -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        block = "\n".join(decision_lines)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f"summary: {title}\n"
            "status: open\n"
            "stage: null\n"
            "contribution: medium\n"
            "created: 2026-05-04\n"
            "closed_at: null\n"
            "human_gate: decision\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            "  - [ ] decide\n"
            "---\n\n"
            f"# {title}\n\n"
            "## Decision required\n\n"
            f"{block}\n"
        )
        (card_dir / "log.md").write_text("")

    def test_long_decision_preview_advertises_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_parked_card(cwd, "long-decision-card", DECISION_LINES)

            result = self.run_goc(cwd, "--no-color", "triage")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            out = result.stdout

            hidden = len(DECISION_LINES) - 6
            # The dropped lines beyond the 6-line cap are recoverable only via
            # the advertised overflow marker, which names how many and where.
            self.assertIn(f"… +{hidden} more lines", out)
            self.assertIn("goc show long-decision-card", out)

    def test_short_decision_preview_has_no_overflow_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_parked_card(cwd, "short-decision-card", DECISION_LINES[:5])

            result = self.run_goc(cwd, "--no-color", "triage")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertNotIn("more lines", result.stdout)


if __name__ == "__main__":
    unittest.main()
