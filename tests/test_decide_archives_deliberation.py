from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DecideArchivesDeliberationTest(unittest.TestCase):
    """`goc decide` must archive the prior `## Decision required` section to
    log.md before replacing it in the README, so the deliberation (options,
    recommendation, trade-offs) survives the dashboard rewrite."""

    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "new":
            (cwd / ".game-of-cards" / "deck").mkdir(parents=True, exist_ok=True)
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

    def test_decide_archives_prior_section_to_log_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "pick-a-default-timeout"
            self.assert_goc_ok(
                self.run_goc(cwd, "new", title, "--gate", "decision", "--tag", "story")
            )

            readme = self.card_dir(cwd, title) / "README.md"
            text = readme.read_text()
            deliberation = (
                "## Decision required\n\n"
                "Pick the default request timeout.\n\n"
                "### Option A — 30s (recommended)\n\n"
                "Safe for slow upstreams.\n\n"
                "### Option B — 5s\n\n"
                "Fails fast but flaky under load.\n"
            )
            readme.write_text(text.rstrip("\n") + "\n\n" + deliberation)

            self.assert_goc_ok(
                self.run_goc(
                    cwd,
                    "decide",
                    title,
                    "--decision",
                    "Use Option A — 30s default",
                    "--because",
                    "Safer for slow upstreams",
                )
            )

            new_readme = readme.read_text()
            log = (self.card_dir(cwd, title) / "log.md").read_text()

            # README is the dashboard: only the resolved decision remains.
            self.assertIn("## Decision\n", new_readme)
            self.assertNotIn("## Decision required", new_readme)
            self.assertNotIn("Option B — 5s", new_readme)

            # log.md is the journal: it archives the deliberation AND records
            # the resolution.
            self.assertIn("decision deliberation archived", log)
            self.assertIn("Option A — 30s (recommended)", log)
            self.assertIn("Option B — 5s", log)
            self.assertIn("decision recorded", log)
            self.assertIn("Use Option A — 30s default", log)

            # The archive precedes the resolution (timeline: filed → decided).
            archive_at = log.index("decision deliberation archived")
            resolved_at = log.index("decision recorded")
            self.assertLess(archive_at, resolved_at)

    def test_decide_without_decision_required_section_records_only_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            title = "no-deliberation-card"
            self.assert_goc_ok(
                self.run_goc(cwd, "new", title, "--gate", "decision", "--tag", "story")
            )

            self.assert_goc_ok(
                self.run_goc(
                    cwd,
                    "decide",
                    title,
                    "--decision",
                    "Go with X",
                    "--because",
                    "It is simplest",
                )
            )

            log = (self.card_dir(cwd, title) / "log.md").read_text()
            self.assertIn("decision recorded", log)
            self.assertNotIn("decision deliberation archived", log)


if __name__ == "__main__":
    unittest.main()
