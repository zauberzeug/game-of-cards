"""`goc validate` flags an absent `summary` key on non-draft cards.

The whitespace-summary card established that a published card's summary
must be non-empty; this extends the same contract to the absent-key case
(goc-new-scaffolds-no-summary-field-so-fresh-cards-pass-validate-without-one).
Draft scaffolds stay exempt — `goc new` output must not be born red.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _write_card(cwd: Path, title: str, *extra_fm_lines: str) -> None:
    card_dir = cwd / ".game-of-cards" / "deck" / title
    card_dir.mkdir(parents=True)
    fm_extra = "".join(f"{line}\n" for line in extra_fm_lines)
    (card_dir / "README.md").write_text(
        "---\n"
        f"title: {title}\n"
        f"{fm_extra}"
        "status: open\n"
        "stage: null\n"
        "contribution: low\n"
        "created: 2026-07-23\n"
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


class ValidateSummaryMissingTest(unittest.TestCase):
    def test_absent_summary_rejected_on_published_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "no-summary-published")

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "no-summary-published: summary: missing — required on published cards",
                result.stderr,
            )

    def test_absent_summary_allowed_on_draft_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "no-summary-draft", "draft: true")

            result = _run_validate(cwd)

            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")

    def test_blank_summary_still_rejected(self) -> None:
        # The absent-key rule extends the present-but-blank rule, it does not
        # replace it (see test_validate_summary_whitespace.py for full coverage).
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            _write_card(cwd, "blank-summary", 'summary: ""')

            result = _run_validate(cwd)

            self.assertNotEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")
            self.assertIn(
                "blank-summary: summary: must not be empty or whitespace-only",
                result.stderr,
            )

    def test_goc_new_summary_flag_lands_in_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            subprocess.run(["git", "init", "-q", str(cwd)], check=True)
            (cwd / ".game-of-cards" / "deck").mkdir(parents=True)
            env = os.environ.copy()
            pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
            )
            result = subprocess.run(
                [
                    sys.executable, "-m", "goc.cli", "new", "card-with-summary-flag",
                    "--summary", "What broke and why it matters.",
                    "--tag", "bug", "--no-commit",
                ],
                cwd=cwd,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=f"stderr:\n{result.stderr}")

            readme = (
                cwd / ".game-of-cards" / "deck" / "card-with-summary-flag" / "README.md"
            )
            fm_lines = readme.read_text().split("---\n")[1].splitlines()
            self.assertIn("summary: What broke and why it matters.", fm_lines)
            # summary sits right after title, matching hand-authored cards
            self.assertTrue(fm_lines[1].startswith("summary:"), msg=fm_lines[:3])


if __name__ == "__main__":
    unittest.main()
