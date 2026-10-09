"""Regression: the draft gate reads the `draft: true` flag alone.

An "unflagged placeholder scaffold" still carries both `goc new`
placeholders, the stub DoD and the stub body, but no `draft: true` flag: a
card scaffolded before the flag existed, or one whose flag was stripped by
hand. `card_is_draft` keys on the flag alone, by the decision recorded on
placeholder-cards-superseded-before-they-are-authored, so such a card is
ordinary queue work. `is_placeholder_scaffold` serves `goc publish` only.

Three engine comments used to say the opposite, that the draft gate also
caught these cards, and two later fixtures repeated the claim. Every test
here builds two twins from `goc new` and strips the flag from one, so the
flag is the only difference between them. The flagged twin is the control:
it proves each surface checked really is draft-gated, so the unflagged
twin passing it is the flag-only contract and not a surface that ignores
drafts altogether.

Regression for engine-comments-claim-unflagged-placeholder-cards-count-as-drafts.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc import engine  # noqa: E402


MARK = engine.DRAFT_MARKER
FLAGGED = "flagged-twin"
UNFLAGGED = "stripped-twin"
SUCCESSOR = "successor-card"

SUCCESSOR_CARD = f"""---
title: {SUCCESSOR}
summary: "An authored card to supersede into."
status: open
stage: null
contribution: medium
created: "2026-10-09T00:00:00Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story]
definition_of_done: |
  - [ ] TDD: a real criterion
---

# {SUCCESSOR}

A real body.
"""


class UnflaggedPlaceholderScaffoldIsNotADraftTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.deck = self.root / ".game-of-cards" / "deck"
        self.deck.mkdir(parents=True)
        for title in (FLAGGED, UNFLAGGED):
            self.ok(self.goc("new", title, "--gate", "none", "--tag", "story"))
        text = self.readme(UNFLAGGED).read_text()
        self.assertEqual(1, text.count("draft: true\n"), msg=text)
        self.readme(UNFLAGGED).write_text(text.replace("draft: true\n", ""))
        (self.deck / SUCCESSOR).mkdir()
        self.readme(SUCCESSOR).write_text(SUCCESSOR_CARD)

    def goc(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("GOC_WORKER", None)
        env["NO_COLOR"] = "1"
        pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = str(ROOT) if not pythonpath else f"{ROOT}{os.pathsep}{pythonpath}"
        return subprocess.run(
            [sys.executable, "-m", "goc.cli", *args],
            cwd=self.root,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def ok(self, result: subprocess.CompletedProcess[str]) -> str:
        self.assertEqual(
            result.returncode, 0, msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        return result.stdout

    def readme(self, title: str) -> Path:
        return self.deck / title / "README.md"

    def card(self, title: str) -> engine.Card:
        return engine.load_card(self.deck / title)

    def json_titles(self, *args: str) -> set[str]:
        return {c["title"] for c in json.loads(self.ok(self.goc("--json", *args)))}

    def test_twins_are_both_placeholder_scaffolds_and_differ_only_in_the_flag(self) -> None:
        def without_title_and_stamps(title: str) -> list[str]:
            text = self.readme(title).read_text().replace(title, "<title>")
            return [
                line for line in text.splitlines()
                if not line.startswith(("created:", "draft:"))
            ]

        self.assertEqual(without_title_and_stamps(FLAGGED), without_title_and_stamps(UNFLAGGED))
        for title in (FLAGGED, UNFLAGGED):
            with self.subTest(title=title):
                self.assertTrue(engine.is_placeholder_scaffold(self.card(title)))
        self.assertTrue(self.card(FLAGGED).draft)
        self.assertFalse(self.card(UNFLAGGED).draft)

    def test_card_is_draft_reads_the_flag_alone(self) -> None:
        self.assertTrue(engine.card_is_draft(self.card(FLAGGED)))
        self.assertFalse(engine.card_is_draft(self.card(UNFLAGGED)))

    def test_json_draft_field_is_false(self) -> None:
        cards = {c["title"]: c for c in json.loads(self.ok(self.goc("--json", "--status", "all")))}
        self.assertIs(True, cards[FLAGGED]["draft"])
        self.assertIs(False, cards[UNFLAGGED]["draft"])
        self.assertIs(False, cards[FLAGGED]["ready"])
        self.assertIs(True, cards[UNFLAGGED]["ready"])

    def test_table_does_not_mark_it(self) -> None:
        table = self.ok(self.goc("--status", "all", "--no-color"))
        rows = {line.split(" ", 1)[0]: line for line in table.splitlines()}
        self.assertTrue(rows[FLAGGED].startswith(f"{FLAGGED} {MARK}"), msg=table)
        self.assertNotIn(MARK, rows[UNFLAGGED], msg=table)

    def test_board_does_not_mark_it(self) -> None:
        board = self.ok(self.goc("--board", "--no-color"))
        cells = {
            cell.strip().split(" ", 1)[0]: cell.strip()
            for line in board.splitlines()
            for cell in line.split(" | ")
            if cell.strip()
        }
        self.assertIn(MARK, cells[FLAGGED], msg=board)
        self.assertNotIn(MARK, cells[UNFLAGGED], msg=board)

    def test_listed_by_the_queue_and_by_ready(self) -> None:
        for args in ((), ("--ready",)):
            with self.subTest(args=args):
                titles = self.json_titles(*args)
                self.assertIn(UNFLAGGED, titles)
                self.assertNotIn(FLAGGED, titles)

    def test_publish_says_it_is_not_a_draft(self) -> None:
        before = self.readme(UNFLAGGED).read_text()
        result = self.goc("publish", UNFLAGGED, "--no-commit")
        self.assertEqual(f"{UNFLAGGED}: not a draft; nothing to publish\n", self.ok(result))
        self.assertEqual(before, self.readme(UNFLAGGED).read_text())
        # The flagged twin reaches the placeholder check and is refused.
        refused = self.goc("publish", FLAGGED, "--no-commit")
        self.assertEqual(2, refused.returncode, msg=refused.stdout + refused.stderr)
        self.assertIn("still an unauthored scaffold", refused.stderr)

    def test_supersede_is_not_refused(self) -> None:
        refused = self.goc("status", FLAGGED, "superseded", "--by", SUCCESSOR, "--no-commit")
        self.assertNotEqual(0, refused.returncode, msg=refused.stdout + refused.stderr)
        self.assertEqual("open", self.card(FLAGGED).status)
        self.ok(self.goc("status", UNFLAGGED, "superseded", "--by", SUCCESSOR, "--no-commit"))
        self.assertEqual("superseded", self.card(UNFLAGGED).status)


if __name__ == "__main__":
    unittest.main()
