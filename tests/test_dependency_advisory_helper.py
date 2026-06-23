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


class DependencyAdvisoryQueueOnlySliceTest(unittest.TestCase):
    """The `queue_only=True` slice consumed by the two human-facing renderers
    (table, board) additionally suppresses the advisory on `active` cards:
    "you may start" is a pull-queue hint with no audience once a card is
    claimed. JSON keeps the default (terminal-only) form.
    """

    def setUp(self) -> None:
        self.prereq = _card("prereq-open", "open", [])
        self.by_title = {"prereq-open": self.prereq}

    def test_open_card_with_open_prereq_shows_advisory(self) -> None:
        card = _card("child", "open", ["prereq-open"])
        self.assertEqual(
            engine.dependency_advisory(card, self.by_title, queue_only=True),
            (["prereq-open"], True),
        )

    def test_active_card_suppresses_advisory(self) -> None:
        card = _card("child", "active", ["prereq-open"])
        self.assertEqual(
            engine.dependency_advisory(card, self.by_title, queue_only=True),
            ([], False),
        )

    def test_terminal_card_suppresses_advisory(self) -> None:
        for terminal_status in sorted(engine.TERMINAL_STATUSES):
            with self.subTest(status=terminal_status):
                card = _card("child", terminal_status, ["prereq-open"])
                self.assertEqual(
                    engine.dependency_advisory(
                        card, self.by_title, queue_only=True
                    ),
                    ([], False),
                )

    def test_default_form_keeps_terminal_only_contract(self) -> None:
        # The machine surface (JSON) consumes the default form: active cards
        # still carry the advisory, only terminal cards are gated out.
        active = _card("child", "active", ["prereq-open"])
        self.assertEqual(
            engine.dependency_advisory(active, self.by_title),
            (["prereq-open"], True),
        )

    def test_table_and_board_agree_per_status(self) -> None:
        # End-to-end: both human-facing renderers must agree on whether the
        # advisory surfaces, for every status. The table prints
        # `awaiting: ... (you may start)`; the board flags the card with ⏳.
        # Both derive from the shared `queue_only=True` slice, so the
        # advisory shows iff the card is open.
        for status in ["open", "active", *sorted(engine.TERMINAL_STATUSES)]:
            with self.subTest(status=status):
                prereq = _card("prereq-open", "open", [])
                child = _card("child", status, ["prereq-open"])
                cards = [prereq, child]
                by_title = {c.title: c for c in cards}

                table = engine.render_table(
                    cards, verbose=2, no_color=True, by_title=by_title
                )
                board = engine.render_board(
                    cards, max_rows=10, no_color=True, by_title=by_title
                )

                table_shows = "awaiting: prereq-open (you may start)" in table
                # The board's ⏳ has other causes (human_gate, impediment);
                # here the child is gate-free and unimpeded, so the only ⏳
                # source for it is the dependency advisory slice.
                board_shows = "child" in board and "⏳" in board

                expected = status == "open"
                self.assertEqual(table_shows, expected)
                self.assertEqual(board_shows, expected)
                self.assertEqual(table_shows, board_shows)


if __name__ == "__main__":
    unittest.main()
