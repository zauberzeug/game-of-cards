from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ValidateDecisionContradictsVerdictTest(unittest.TestCase):
    """`goc validate` must emit an advisory `WARN DECISION_CONTRADICTS_VERDICT`
    for a non-terminal card carrying a resolved `## Decision` whose text
    re-scopes/reverses a prior verdict while the summary/banner still asserts
    that verdict. The warning is advisory only — `validate` still exits 0 —
    and must NOT fire for terminal cards, decisions without reversal markers,
    or summaries without a negative-verdict token."""

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

    def write_card(
        self,
        cwd: Path,
        title: str,
        *,
        status: str = "open",
        summary: str,
        decision_block: str,
    ) -> None:
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        done = "x" if status == "done" else " "
        closed_at = "2026-05-04" if status in {"done", "disproved", "superseded"} else "null"
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f'summary: "{summary}"\n'
            f"status: {status}\n"
            "stage: null\n"
            "contribution: low\n"
            "created: 2026-05-04\n"
            f"closed_at: {closed_at}\n"
            "human_gate: none\n"
            "advances: []\n"
            "advanced_by: []\n"
            "tags: [bug]\n"
            "definition_of_done: |\n"
            f"  - [{done}] PROCESS: test card\n"
            "---\n\n"
            f"# {title}\n\n"
            f"{decision_block}\n"
        )
        (card_dir / "log.md").write_text("")

    RESCOPE_DECISION = (
        "## Decision\n\n"
        "*Resolved 2026-05-04:* Re-scope: approach X is viable under condition Y.\n\n"
        "*Reasoning:* The refutation no longer holds under Y.\n"
    )
    PLAIN_DECISION = (
        "## Decision\n\n"
        "*Resolved 2026-05-04:* Go with option B.\n\n"
        "*Reasoning:* Simplest path.\n"
    )
    NEGATIVE_SUMMARY = "VERDICT: approach X is REFUTED — it never converges."
    NEUTRAL_SUMMARY = "Tracks whether approach X should ship under condition Y."

    def test_warns_on_rescope_decision_over_negative_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "approach-x-is-unviable",
                summary=self.NEGATIVE_SUMMARY,
                decision_block=self.RESCOPE_DECISION,
            )
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN DECISION_CONTRADICTS_VERDICT approach-x-is-unviable",
                result.stderr,
            )

    def test_no_warn_for_terminal_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # A disproved card legitimately carries a negative verdict.
            self.write_card(
                cwd,
                "approach-x-disproved",
                status="disproved",
                summary=self.NEGATIVE_SUMMARY,
                decision_block=self.RESCOPE_DECISION,
            )
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("DECISION_CONTRADICTS_VERDICT", result.stderr)

    def test_no_warn_when_decision_lacks_reversal_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "approach-x-is-unviable",
                summary=self.NEGATIVE_SUMMARY,
                decision_block=self.PLAIN_DECISION,
            )
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("DECISION_CONTRADICTS_VERDICT", result.stderr)

    def test_no_warn_when_summary_has_no_negative_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "approach-x-tracking",
                summary=self.NEUTRAL_SUMMARY,
                decision_block=self.RESCOPE_DECISION,
            )
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("DECISION_CONTRADICTS_VERDICT", result.stderr)


if __name__ == "__main__":
    unittest.main()
