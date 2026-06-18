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


if __name__ == "__main__":
    unittest.main()
