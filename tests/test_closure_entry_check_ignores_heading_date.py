"""`goc attest`'s `log-md-closure-entry` check accepts a closure heading of any date.

The closer types the heading's stamp by hand (`Skill(finish-card)` Step 4), so
the check used to compare the closer's clock with attest's: a closure entry
written before UTC midnight failed an attest run after it, so did any re-run on
a later day, and so did a stamp typed by a closer whose clock ran ahead. log.md
is append-only, so the only way back to a pass was a duplicate closure entry
(card closure-log-attestation-misfires-across-utc-midnight). The check now asks
whether a well-formed closure heading exists at all — and must still fail a
log.md that has none, including one that holds only attest's own verification
block, or a failed run would turn the next one green by itself.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402

TITLE = "closing-card"
CHECK = {"name": "log-md-closure-entry", "kind": "derived"}
# The attest run one minute after the UTC midnight that the headings below precede.
ATTEST_TODAY = "2026-05-27T00:01:00Z"
NO_CLOSURE_YET = "## 2026-05-26T23:50:00Z: decision recorded\n\nNot closed yet.\n"


def _closure_entry(stamp: str) -> str:
    return f"## {stamp} — Closure\n\n- **What changed**: the fix landed.\n"


class ClosureEntryPredicateTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.deck = Path(tmp.name)
        (self.deck / TITLE).mkdir()
        previous = engine.DECK_DIR
        engine.DECK_DIR = self.deck
        self.addCleanup(setattr, engine, "DECK_DIR", previous)
        self.card = engine.Card(
            title=TITLE,
            path=self.deck / TITLE,
            frontmatter={"title": TITLE, "status": "active"},
            body="",
            dod_open=0,
            dod_done=1,
        )

    def _check(self, log_text: str | None, today: str = ATTEST_TODAY) -> tuple[bool, str]:
        if log_text is not None:
            (self.deck / TITLE / "log.md").write_text(log_text)
        return engine._run_derived_check(CHECK, self.card, [self.card], today)

    def test_heading_written_before_utc_midnight_passes_after_it(self) -> None:
        ok, summary = self._check(_closure_entry("2026-05-26T23:59:00Z"))

        self.assertTrue(ok, summary)
        self.assertEqual("'## 2026-05-26T23:59:00Z — Closure' present", summary)

    def test_heading_from_any_earlier_day_passes(self) -> None:
        # Date-only is the legacy form; the older stamps are a re-run days later,
        # e.g. once an `advanced_by` prerequisite has closed.
        for stamp in ("2026-05-26", "2026-05-20T08:00:00Z", "2025-12-31T23:59:59Z"):
            with self.subTest(stamp=stamp):
                ok, summary = self._check(_closure_entry(stamp))

                self.assertTrue(ok, summary)
                self.assertEqual(f"'## {stamp} — Closure' present", summary)

    def test_heading_stamped_ahead_of_attests_clock_passes(self) -> None:
        # A closer whose clock runs eight hours ahead types tomorrow's date at
        # 20:00Z. This deck holds closure headings stamped up to eight hours
        # after the attest run that verified them.
        ok, summary = self._check(_closure_entry("2026-05-27T04:00:00Z"), today="2026-05-26T20:00:00Z")

        self.assertTrue(ok, summary)

    def test_summary_names_the_latest_heading(self) -> None:
        log = _closure_entry("2026-05-20T08:00:00Z") + "\n" + _closure_entry("2026-05-26T23:59:00Z")

        ok, summary = self._check(log)

        self.assertTrue(ok, summary)
        self.assertEqual("'## 2026-05-26T23:59:00Z — Closure' present", summary)

    def test_missing_log_fails(self) -> None:
        self.assertEqual((False, "log.md missing"), self._check(None))

    def test_log_without_a_closure_heading_fails(self) -> None:
        ok, summary = self._check(NO_CLOSURE_YET)

        self.assertFalse(ok)
        self.assertEqual("no '## YYYY-MM-DDTHH:MM:SSZ — Closure' section", summary)

    def test_attests_own_block_never_satisfies_the_check(self) -> None:
        """Neither a failed run's block nor a passing one stands in for the entry.

        Dates no longer filter anything, so the line anchor is all that keeps a
        block `_cmd_attest` wrote — whose result line quotes a closure heading —
        from passing the next run with no closure entry in the log.
        """
        failed = (False, "no '## YYYY-MM-DDTHH:MM:SSZ — Closure' section")
        passed = (True, "'## 2026-05-26T23:59:00Z — Closure' present")
        for label, (verdict, summary) in (("failed run", failed), ("passing run", passed)):
            with self.subTest(block=label):
                block = engine._format_attestation_block(
                    ATTEST_TODAY,
                    [{"layer": 3, "name": CHECK["name"], "passed": verdict, "summary": summary}],
                )

                ok, result = self._check(NO_CLOSURE_YET + "\n" + block)

                self.assertFalse(ok, f"attest's own block satisfied the check ({result}):\n{block}")


class ClosureEntryAttestPathTest(unittest.TestCase):
    """The shipped path: the real `goc attest`, on the real UTC clock."""

    CONFIG = "layer_2_project_dod: []\nlayer_3_goc_dod:\n  - name: log-md-closure-entry\n    kind: derived\n"
    README = f"""\
---
title: {TITLE}
summary: "An active card about to close."
status: active
stage: null
contribution: low
created: "2026-01-01T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: the work is done
---

# {TITLE}
"""

    def test_attest_passes_a_closure_entry_written_before_the_last_utc_midnight(self) -> None:
        # No clock is faked: a heading stamped 23:59:00Z yesterday is the log a
        # closure entry written before the last midnight leaves for this run.
        yesterday = (datetime.now(tz=timezone.utc) - timedelta(days=1)).date().isoformat()
        stamp = f"{yesterday}T23:59:00Z"
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            (cwd / ".game-of-cards").mkdir()
            (cwd / ".game-of-cards" / "config.yaml").write_text(self.CONFIG)
            card_dir = cwd / ".game-of-cards" / "deck" / TITLE
            card_dir.mkdir(parents=True)
            (card_dir / "README.md").write_text(self.README)
            (card_dir / "log.md").write_text(_closure_entry(stamp))
            env = os.environ.copy()
            pythonpath = env.get("PYTHONPATH")
            env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
            env.pop("GOC_WORKTREE_DECK", None)

            result = subprocess.run(
                [sys.executable, "-m", "goc.cli", "attest", TITLE, "--non-interactive"],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}")
            expected = f"log-md-closure-entry — '## {stamp} — Closure' present"
            self.assertIn(f"[x] {expected}", result.stdout)
            self.assertIn(f"- [x] {expected}", (card_dir / "log.md").read_text())


if __name__ == "__main__":
    unittest.main()
