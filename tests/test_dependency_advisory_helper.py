"""Unit test for the centralized `dependency_advisory` helper.

The "awaiting: X — you may start" advisory is a liveness-gated display of
`dependency_blockers` / `dependency_blocked`: meaningless on a terminal card.
That `status not in TERMINAL_STATUSES` gate used to be re-inlined in all three
renderers (board `card_cell`, `render_table`, `render_json`) and drifted into a
shipping bug twice. `dependency_advisory` centralizes the gate so the renderers
consume a pre-gated `(blockers, has_blockers)` result; this test pins both
branches directly.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from goc import engine


def _card(title: str, status: str, advanced_by: list[str]) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": status,
            "contribution": "medium",
            "human_gate": "none",
            "created": "2026-06-20",
            "summary": f"{title} summary",
            "tags": [],
            "advances": [],
            "advanced_by": advanced_by,
            "supersedes": [],
            "superseded_by": [],
            "definition_of_done": "- [x] done\n",
        },
        body="body",
        dod_open=0,
        dod_done=1,
    )


class DependencyAdvisoryHelperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.prereq = _card("prereq-open", "open", [])
        self.by_title = {"prereq-open": self.prereq}

    def test_terminal_card_returns_empty_and_false(self) -> None:
        for terminal_status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(status=terminal_status):
                card = _card("child", terminal_status, ["prereq-open"])
                self.assertEqual(
                    engine.dependency_advisory(card, self.by_title),
                    ([], False),
                )

    def test_live_card_returns_live_blockers(self) -> None:
        card = _card("child", "open", ["prereq-open"])
        self.assertEqual(
            engine.dependency_advisory(card, self.by_title),
            (["prereq-open"], True),
        )

    def test_live_card_with_no_prereqs_returns_empty_and_false(self) -> None:
        card = _card("child", "open", [])
        self.assertEqual(
            engine.dependency_advisory(card, self.by_title),
            ([], False),
        )

    def test_live_card_ignores_terminal_prereqs(self) -> None:
        done_prereq = _card("prereq-done", "done", [])
        by_title = {"prereq-done": done_prereq}
        card = _card("child", "open", ["prereq-done"])
        self.assertEqual(
            engine.dependency_advisory(card, by_title),
            ([], False),
        )

    def test_helper_bool_is_truthiness_of_blockers(self) -> None:
        card = _card("child", "active", ["prereq-open"])
        blockers, flag = engine.dependency_advisory(card, self.by_title)
        self.assertEqual(flag, bool(blockers))


if __name__ == "__main__":
    unittest.main()
