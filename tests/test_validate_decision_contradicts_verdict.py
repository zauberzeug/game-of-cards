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
    # Same re-scope decision under the heading `Skill(create-card)` writes when
    # the project rubric pre-resolves a gate-`none` card.
    RESCOPE_DECISION_RUBRIC = (
        "## Decision (rubric-derived)\n\n"
        "*Resolved 2026-05-04:* Re-scope: approach X is viable under condition Y.\n\n"
        "*Reasoning:* The refutation no longer holds under Y.\n"
    )
    # A *pending* section carrying re-scope language must never be read as a
    # resolved decision — it is the question, not the answer.
    RESCOPE_DECISION_REQUIRED = (
        "## Decision required\n\n"
        "Should we re-scope: is approach X viable under condition Y?\n"
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

    def test_warns_on_rubric_derived_rescope_decision(self) -> None:
        # The `## Decision (rubric-derived)` heading is a first-class resolved
        # decision (create-card writes it), so the coherence check must apply.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "approach-x-is-unviable",
                summary=self.NEGATIVE_SUMMARY,
                decision_block=self.RESCOPE_DECISION_RUBRIC,
            )
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "WARN DECISION_CONTRADICTS_VERDICT approach-x-is-unviable",
                result.stderr,
            )

    def test_no_warn_for_pending_decision_required_section(self) -> None:
        # A pending `## Decision required` section is the question, not a
        # resolved decision — re-scope language inside it must not flag.
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(
                cwd,
                "approach-x-is-unviable",
                summary=self.NEGATIVE_SUMMARY,
                decision_block=self.RESCOPE_DECISION_REQUIRED,
            )
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertNotIn("DECISION_CONTRADICTS_VERDICT", result.stderr)

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

    # ── status names and everyday words are not verdicts or reversals ──
    # verdict-coherence-check-mistakes-the-disproved-status-name-for-a-negative-verdict:
    # on 2026-10-22 a summary listing the terminal statuses under a decision
    # saying "no longer" fired the check on five coherent cards.

    STATUS_NAME_SUMMARY = (
        "Probe the cache; the card flips to `disproved` if the probe fails, "
        "or the card is disproved by the next release."
    )
    STATUS_LIST_SUMMARY = (
        "goc wait mutates cards whose status is already terminal "
        "(`done`/`disproved`/`superseded`) with no guard."
    )
    EVERYDAY_DECISION = (
        "## Decision\n\n"
        "*Resolved 2026-10-22:* Use the shared helper instead of the inline check.\n\n"
        "*Reasoning:* _cmd_decide no longer refuses terminal cards, so there is "
        "no message left to mirror.\n"
    )

    def assert_warns(self, summary: str, decision_block: str, *, warns: bool) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_card(cwd, "probe-card", summary=summary, decision_block=decision_block)
            result = self.run_goc(cwd, "validate", "--quiet")
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            check = self.assertIn if warns else self.assertNotIn
            check("DECISION_CONTRADICTS_VERDICT probe-card", result.stderr)

    def test_no_warn_for_the_2026_10_22_shape(self) -> None:
        # The incident itself: a status list under an everyday decision.
        self.assert_warns(self.STATUS_LIST_SUMMARY, self.EVERYDAY_DECISION, warns=False)

    def test_no_warn_when_summary_only_names_the_disproved_status(self) -> None:
        # A genuine re-scope decision, so only the verdict side can silence it.
        for summary in (self.STATUS_NAME_SUMMARY, self.STATUS_LIST_SUMMARY):
            with self.subTest(summary=summary):
                self.assert_warns(summary, self.RESCOPE_DECISION, warns=False)

    def test_no_warn_when_decision_only_uses_everyday_words(self) -> None:
        # A genuine negative verdict, so only the marker side can silence it.
        self.assert_warns(self.NEGATIVE_SUMMARY, self.EVERYDAY_DECISION, warns=False)

    def test_warns_when_a_verdict_uses_the_status_word(self) -> None:
        # `disproved` used as a verdict, not as a status name, still counts.
        for summary in (
            "DISPROVED: approach X never converges.",
            "Verdict: DISPROVED (2026-07-11). Approach X never converges.",
            "The hypothesis was disproved by the benchmark.",
        ):
            with self.subTest(summary=summary):
                self.assert_warns(summary, self.RESCOPE_DECISION, warns=True)

    def test_warns_when_decision_says_the_refutation_no_longer_holds(self) -> None:
        # "no longer" before a verdict word is still a reversal on its own.
        decision = (
            "## Decision\n\n"
            "*Resolved 2026-05-04:* Pursue approach X: the refutation no longer "
            "holds under condition Y.\n\n"
            "*Reasoning:* New benchmark.\n"
        )
        self.assert_warns(self.NEGATIVE_SUMMARY, decision, warns=True)


class VerdictTokensReadProseOnlyTest(unittest.TestCase):
    """`negative_verdict` / `rescope_marker` skip a token that only names
    something — a status name in a list or after a status cue, a code span,
    a card slug or field name — and keep every token that asserts."""

    def setUp(self) -> None:
        sys.path.insert(0, str(ROOT))
        from goc import engine

        self.engine = engine

    def test_negative_verdict(self) -> None:
        asserts = [
            "REFUTED: approach X never converges.",
            "Verdict: DISPROVED (2026-07-11).",
            "Disproved 2026-06-24. No misalignment occurs.",
            "The hypothesis was disproved by the benchmark.",
            "approach X does not work on Windows",
            "Do not pursue the inline variant.",
        ]
        names = [
            "the card flips to `disproved` if the probe fails",
            "the card flips to disproved if the probe fails",
            "or the card is disproved by the next release",
            "terminal (done/disproved/superseded) cards",
            "a disproved or superseded card",
            "{done, disproved, superseded}",
            "the board's DONE, DISPROVED and SUPERSEDED columns",
            "goc status <t> disproved refuses",
            "the status disproved is terminal",
            "mark this disproved",
            "closed as disproved",
            "see closure-gate-rejects-superseded-or-disproved-prereqs",
        ]
        for text in asserts:
            with self.subTest(asserts=text):
                self.assertIsNotNone(self.engine.negative_verdict(text))
        for text in names:
            with self.subTest(names=text):
                self.assertIsNone(self.engine.negative_verdict(text))

    def test_rescope_marker(self) -> None:
        asserts = [
            "Re-scope: approach X is viable under condition Y.",
            "Reverse: approach X is no longer refuted; pursue it.",
            "The refutation no longer holds under Y.",
            "Supersede by new-card-title.",
            "the earlier note was wrong",
            "approach X is now viable",
        ]
        names = [
            "Use the helper instead of the inline check.",
            "_cmd_decide no longer refuses terminal cards",
            "the validator rejects status:superseded with empty superseded_by",
            "Card was closed as superseded on 2026-05-08",
            "see goc-decide-leaves-stale-verdict-content-when-recording-a-rescope",
            "loosening the superseded gate is rejected",
        ]
        for text in asserts:
            with self.subTest(asserts=text):
                self.assertIsNotNone(self.engine.rescope_marker(text))
        for text in names:
            with self.subTest(names=text):
                self.assertIsNone(self.engine.rescope_marker(text))


if __name__ == "__main__":
    unittest.main()
