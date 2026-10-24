"""Regression: every verb that releases a card from draft refuses a missing summary.

Card: draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck
(decision 2026-10-06: option 1 — refuse at the draft-clearing verbs).

`goc validate` requires `summary` on every non-draft card, but `publish`,
`status <t> active`, `done` and `done --bundle` cleared `draft: true` without
looking at it. A first-party verb sequence therefore left the deck red until
the next validate run. These tests pin both directions for each verb: refused
without a valid summary (exit 2, card untouched), released with one (and the
deck then validates). Transitions that do not clear a draft flag stay ungated —
the verbs must not make a summary-less card worse, but they do not take over
validate's job for cards that were never drafts.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DraftClearingVerbsRequireSummaryTest(unittest.TestCase):
    def run_goc(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args and args[0] == "new":
            (cwd / ".game-of-cards" / "deck").mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=120,
        )

    def assert_ok(self, result: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(result.returncode, 0, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")

    def readme_path(self, cwd: Path, title: str) -> Path:
        return cwd / ".game-of-cards" / "deck" / title / "README.md"

    def new_authored_draft(self, cwd: Path, title: str, summary: str | None) -> Path:
        args = ["new", title, "--gate", "none", "--tag", "story"]
        if summary is not None:
            args += ["--summary", summary]
        self.assert_ok(self.run_goc(cwd, *args))
        path = self.readme_path(cwd, title)
        text = path.read_text()
        text = text.replace("- [ ] (replace with real criteria)", "- [x] MECHANICAL: real criterion met")
        text = text.replace("(write the design doc here)", "Real authored body.")
        path.write_text(text)
        self.assertIn("\ndraft: true\n", text)
        return path

    def assert_refused_untouched(self, result: subprocess.CompletedProcess[str], path: Path, before: str) -> None:
        self.assertEqual(result.returncode, 2, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
        self.assertIn("summary:", result.stderr)
        self.assertEqual(path.read_text(), before, "a refused verb must not mutate the card")

    VERBS = {
        "publish": ("publish", "card-a", "--no-commit"),
        "status active": ("status", "card-a", "active", "--worker-who", "test-worker", "--no-commit"),
        "done": ("done", "card-a"),
    }

    def test_each_draft_clearing_verb_refuses_a_draft_without_summary(self) -> None:
        for name, argv in self.VERBS.items():
            with self.subTest(verb=name), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                path = self.new_authored_draft(cwd, "card-a", summary=None)
                before = path.read_text()
                self.assert_refused_untouched(self.run_goc(cwd, *argv), path, before)

    def test_each_draft_clearing_verb_releases_a_draft_with_summary(self) -> None:
        for name, argv in self.VERBS.items():
            with self.subTest(verb=name), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                path = self.new_authored_draft(cwd, "card-a", summary="Authored one-line summary.")
                self.assert_ok(self.run_goc(cwd, *argv))
                self.assertNotIn("draft:", path.read_text())
                self.assert_ok(self.run_goc(cwd, "validate"))

    def test_invalid_summary_forms_are_refused_like_validate_refuses_them(self) -> None:
        for value in ("null", '""', '"   "', "42"):
            with self.subTest(summary=value), tempfile.TemporaryDirectory() as tmp:
                cwd = Path(tmp)
                path = self.new_authored_draft(cwd, "card-a", summary=None)
                text = path.read_text().replace("title: card-a\n", f"title: card-a\nsummary: {value}\n")
                path.write_text(text)
                self.assert_refused_untouched(
                    self.run_goc(cwd, "status", "card-a", "active", "--no-commit"), path, text)

    def test_done_bundle_refuses_before_closing_any_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            good = self.new_authored_draft(cwd, "card-good", summary="Has a summary.")
            bad = self.new_authored_draft(cwd, "card-bad", summary=None)
            before = {good: good.read_text(), bad: bad.read_text()}
            result = self.run_goc(cwd, "done", "--bundle", "card-good", "card-bad")
            self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
            self.assertIn("card-bad", result.stderr)
            for path, text in before.items():
                self.assertEqual(path.read_text(), text, f"{path.parent.name} must stay untouched")

    def test_a_card_that_is_not_a_draft_is_not_newly_gated(self) -> None:
        """Scope: only the draft → published transition is gated; validate stays the net
        for cards that never were drafts (e.g. written by hand)."""
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            path = self.new_authored_draft(cwd, "card-a", summary="Temporary summary.")
            self.assert_ok(self.run_goc(cwd, "publish", "card-a", "--no-commit"))
            path.write_text(path.read_text().replace('summary: "Temporary summary."\n', "").replace(
                "summary: Temporary summary.\n", ""))
            self.assertNotIn("summary:", path.read_text())
            self.assert_ok(self.run_goc(cwd, "status", "card-a", "active",
                                        "--worker-who", "test-worker", "--no-commit"))


if __name__ == "__main__":
    unittest.main()
