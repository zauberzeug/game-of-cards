"""Regression: the verbose table's `awaiting: ... (you may start)`
dependency advisory must only render for live (non-terminal) cards.

Before the fix, `render_table` computed `dependency_blockers` for every
card regardless of its own status, so a terminal card (done / disproved /
superseded) that still carried a non-terminal `advanced_by` prereq was
labelled `awaiting: <prereq> (you may start)` — nonsensical on a card that
cannot start, and a drift from the board renderer, which gates the same
signal behind `t.status not in TERMINAL_STATUSES`.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from goc import engine


def _card(title: str, status: str, advanced_by: list[str], created: str) -> engine.Card:
    return engine.Card(
        title=title,
        path=Path(f"/tmp/{title}/README.md"),
        frontmatter={
            "title": title,
            "status": status,
            "contribution": "medium",
            "human_gate": "none",
            "created": created,
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


def _awaiting_lines_for(out: str, title: str) -> list[str]:
    """Return the indented `awaiting:` lines that belong to `title`'s block."""
    lines = out.splitlines()
    found: list[str] = []
    in_block = False
    for line in lines:
        if line.startswith(title + " ") or line == title:
            in_block = True
            continue
        if in_block:
            if line.startswith("    "):
                if line.strip().startswith("awaiting:"):
                    found.append(line.strip())
            else:
                in_block = False
    return found


class VerboseTableAwaitingLivenessTest(unittest.TestCase):
    def test_terminal_card_omits_awaiting_live_card_keeps_it(self) -> None:
        prereq = _card("prereq-open", "open", [], "2026-06-18")
        live = _card("live-child", "open", ["prereq-open"], "2026-06-17")
        cards = [live, prereq]

        for terminal_status in ("done", "disproved", "superseded"):
            with self.subTest(status=terminal_status):
                closed = _card(
                    "closed-child", terminal_status, ["prereq-open"], "2026-06-17"
                )
                out = engine.render_table(
                    [closed, live, prereq], verbose=1, no_color=True
                )
                # The terminal card must NOT carry an awaiting advisory.
                self.assertEqual(
                    _awaiting_lines_for(out, "closed-child"),
                    [],
                    msg=f"terminal ({terminal_status}) card showed an awaiting "
                    f"advisory:\n{out}",
                )
                # A live card with the same open prereq still shows it.
                self.assertEqual(
                    _awaiting_lines_for(out, "live-child"),
                    ["awaiting: prereq-open (you may start)"],
                    msg=f"live card lost its awaiting advisory:\n{out}",
                )

    def test_active_card_omits_awaiting_and_agrees_with_board(self) -> None:
        # `(you may start)` is a pull-queue hint with no audience on an
        # already-claimed `active` card. The board's not_ready gate already
        # surfaces the dependency advisory only for open cards; the table
        # must agree (the two human-facing renderers consume the same
        # `dependency_advisory` helper but the board adds the open-only
        # slice — the table now mirrors it).
        prereq = _card("prereq-open", "open", [], "2026-06-18")
        active = _card("active-child", "active", ["prereq-open"], "2026-06-17")
        live = _card("open-child", "open", ["prereq-open"], "2026-06-17")
        cards = [active, live, prereq]

        out = engine.render_table(cards, verbose=1, no_color=True)
        # The active card must NOT carry an awaiting advisory.
        self.assertEqual(
            _awaiting_lines_for(out, "active-child"),
            [],
            msg=f"active card showed an awaiting advisory:\n{out}",
        )
        # An open card with the same prereq still shows it.
        self.assertEqual(
            _awaiting_lines_for(out, "open-child"),
            ["awaiting: prereq-open (you may start)"],
            msg=f"open card lost its awaiting advisory:\n{out}",
        )

        # The board agrees: it flags the open card's dependency advisory
        # with the hourglass but leaves the active card unmarked.
        board = engine.render_board(cards, no_color=True, max_rows=100)
        self.assertIn(
            "open-child [m] ⏳",
            board,
            msg=f"board dropped the open card's dependency marker:\n{board}",
        )
        self.assertNotIn(
            "active-child [m] ⏳",
            board,
            msg=f"board flagged the active card's dependency advisory:\n{board}",
        )


if __name__ == "__main__":
    unittest.main()
