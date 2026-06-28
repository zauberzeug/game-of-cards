from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LONG_SUMMARY = (
    "This card needs a human decision about whether to adopt approach A or "
    "approach B for the new export pipeline, and the tradeoffs around latency, "
    "memory, and operational complexity are subtle enough that we should not "
    "auto-pick one without a maintainer weighing in on the rollout risk."
)


class TriageSummaryPreviewOverflowTest(unittest.TestCase):
    """The summary-fallback preview branch (card has a `summary` but no
    `## Decision required` section) must advertise its clip the same way the
    decision_required branch does — never hard-cut at 140 chars silently."""

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

    def write_parked_card(self, cwd: Path, title: str, summary: str) -> None:
        # No `## Decision required` section — exercises the summary fallback.
        card_dir = cwd / ".game-of-cards" / "deck" / title
        card_dir.mkdir(parents=True)
        (card_dir / "README.md").write_text(
            "---\n"
            f"title: {title}\n"
            f'summary: "{summary}"\n'
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
            "Body with no decision-required section.\n"
        )
        (card_dir / "log.md").write_text("")

    def test_long_summary_preview_advertises_clip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            self.write_parked_card(cwd, "long-summary-card", LONG_SUMMARY)

            result = self.run_goc(cwd, "--no-color", "triage")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            out = result.stdout

            # The clipped tail is recoverable only via the advertised pointer.
            self.assertIn("…", out)
            self.assertIn("goc show long-summary-card", out)
            # And the clip must not masquerade as the whole summary.
            self.assertNotIn(LONG_SUMMARY, out)

    def test_short_summary_preview_has_no_clip_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            short = "Decide whether to keep the legacy export path."
            self.write_parked_card(cwd, "short-summary-card", short)

            result = self.run_goc(cwd, "--no-color", "triage")
            self.assertEqual(0, result.returncode, msg=result.stderr)
            out = result.stdout

            self.assertIn(short, out)
            self.assertNotIn("goc show short-summary-card", out)


if __name__ == "__main__":
    unittest.main()
