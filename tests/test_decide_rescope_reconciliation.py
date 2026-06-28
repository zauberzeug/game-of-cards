from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DecideRescopeReconciliationTest(unittest.TestCase):
    """`goc decide` must, when the `--decision` text reads like a re-scope or
    reversal of a prior verdict, print a reconciliation reminder: the card's
    summary, body banner / DoD, and its advances/advanced_by neighbor
    references are NOT auto-updated, and a true re-scope should prefer
    `goc status … superseded --by …`. A plain decision must print NO such
    reminder (no false positive)."""

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

    def assert_goc_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}",
        )

    def card_dir(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title

    def make_verdict_card(
        self,
        cwd: Path,
        title: str,
        *,
        advances: list[str] | None = None,
        advanced_by: list[str] | None = None,
    ) -> None:
        """A decision-gated card whose summary + body assert a NEGATIVE verdict."""
        self.assert_goc_ok(self.run_goc(cwd, "new", title, "--gate", "decision", "--tag", "story"))
        readme = self.card_dir(cwd, title) / "README.md"
        text = readme.read_text()
        # `goc new` scaffolds no `summary:` line; inject one carrying a strong
        # negative verdict, then add a body banner asserting the same.
        text = text.replace(
            f"title: {title}\n",
            f"title: {title}\n"
            'summary: "VERDICT: approach X is REFUTED — the benchmark never converges."\n',
            1,
        )
        for field, items in (("advances", advances), ("advanced_by", advanced_by)):
            if items:
                block = "\n".join(f"  - {it}" for it in items)
                text = text.replace(f"{field}: []", f"{field}:\n{block}")
        # Banner sits ABOVE the `## Decision required` section so it survives
        # the section replacement `goc decide` performs (a banner *inside* the
        # section would be archived to log.md, not left stale).
        body_tail = (
            "> ⚠ REFUTED: approach X does not work. Do not pursue.\n"
            "\n"
            "## Decision required\n"
            "\n"
            "Should we keep pursuing approach X?\n"
        )
        readme.write_text(text.rstrip("\n") + "\n\n" + body_tail)

    def test_rescope_decision_prints_reconciliation_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "approach-x-is-unviable"
            self.make_verdict_card(cwd, title)

            result = self.run_goc(
                cwd,
                "decide",
                title,
                "--decision",
                "Re-scope: approach X is viable under condition Y.",
                "--because",
                "The refutation was specific to condition Z; under Y it converges.",
            )
            self.assert_goc_ok(result)
            out = result.stdout + result.stderr
            # Names the situation as a re-scope/reversal.
            self.assertIn("re-scope", out.lower())
            # Says the other surfaces are NOT auto-updated.
            self.assertIn("not auto-updated", out.lower().replace("‑", "-"))
            # Echoes the summary and flags that it still asserts a negative verdict.
            self.assertIn("summary", out.lower())
            self.assertIn("REFUTED", out)
            self.assertIn("still asserts a negative verdict", out)
            # Names the persisted body banner as a stale surface.
            self.assertIn("banner", out.lower())
            # Points at the sanctioned supersede path.
            self.assertIn("superseded --by", out)

    def test_rescope_reminder_lists_neighbor_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            # Neighbors must exist as real cards so the edge is valid.
            self.assert_goc_ok(self.run_goc(cwd, "new", "tracking-epic", "--tag", "epic"))
            self.assert_goc_ok(self.run_goc(cwd, "new", "downstream-task", "--tag", "story"))
            title = "approach-x-is-unviable"
            self.make_verdict_card(
                cwd, title, advances=["tracking-epic"], advanced_by=["downstream-task"]
            )

            result = self.run_goc(
                cwd,
                "decide",
                title,
                "--decision",
                "Reverse: approach X is no longer refuted; pursue it.",
                "--because",
                "New evidence overturns the original benchmark.",
            )
            self.assert_goc_ok(result)
            out = result.stdout + result.stderr
            self.assertIn("tracking-epic", out)
            self.assertIn("downstream-task", out)

    def test_plain_decision_prints_no_reminder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "approach-x-is-unviable"
            self.make_verdict_card(cwd, title)

            result = self.run_goc(
                cwd,
                "decide",
                title,
                "--decision",
                "Go with option B.",
                "--because",
                "It is the simplest path that satisfies the requirement.",
            )
            self.assert_goc_ok(result)
            out = (result.stdout + result.stderr).lower()
            self.assertNotIn("re-scope", out)
            self.assertNotIn("not auto-updated", out.replace("‑", "-"))


if __name__ == "__main__":
    unittest.main()
