"""Regression: sort_default's near-term-flow tiebreak counts live downstream
cards across the FULL deck, not just the filtered subset being sorted.

The GRPW sort key is (-value, -live_direct, created). `value` is computed on
the full deck and threaded in; the `live_direct` tiebreak must see the same
full graph. When a card's `advances` target is live but hidden by the display
filter (e.g. an `active` target while sorting the `open` column), it still
unblocks flow and must count. Before the fix, `live_direct` built its lookup
from whatever list it was handed, so filtered-out-but-live targets scored 0 —
collapsing the tiebreak to age and inverting equal-value cards.

See the card
`scheduler-tiebreak-undercounts-downstream-flow-through-filtered-out-cards`.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from goc.engine import Card, compute_values, sort_default


def _mk(title: str, status: str, contribution: str, advances, created: str) -> Card:
    fm: dict = {
        "title": title,
        "status": status,
        "contribution": contribution,
        "human_gate": "none",
        "advances": list(advances),
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [ ] X\n",
        "created": created,
    }
    return Card(
        title=title,
        path=Path(f"/tmp/{title}"),
        frontmatter=fm,
        body="",
        dod_open=1,
        dod_done=0,
    )


class SortDefaultFullDeckTiebreakTest(unittest.TestCase):
    def test_filtered_out_live_target_still_counts_in_tiebreak(self) -> None:
        # A and X tie on value; A unblocks two live downstream cards, X one.
        # A is the *newer* card, so age alone would rank X first — only the
        # live-flow tiebreak puts A on top.
        a = _mk("a-two-live", "open", "medium",
                ["h-active", "l-active"], "2026-01-02")
        x = _mk("x-one-live", "open", "medium", ["h-active"], "2026-01-01")
        h = _mk("h-active", "active", "high", [], "2026-01-01")
        ell = _mk("l-active", "active", "low", [], "2026-01-01")
        full = [a, x, h, ell]

        values = compute_values(full)
        self.assertAlmostEqual(
            values["a-two-live"][0], values["x-one-live"][0],
            msg="precondition: A and X must tie on value for the tiebreak to decide",
        )

        full_by_title = {c.title: c for c in full}
        open_subset = [c for c in full if c.status == "open"]

        order = [
            c.title
            for c in sort_default(open_subset, values=values, by_title=full_by_title)
        ]
        self.assertEqual(
            order,
            ["a-two-live", "x-one-live"],
            "full-deck by_title must let the tiebreak count the active "
            f"downstream cards; got {order}",
        )

    def test_genuinely_dangling_edge_still_counts_zero(self) -> None:
        # A target absent from the *whole* deck (not merely filtered out) is a
        # dangling edge and must contribute 0 — so age decides, oldest first.
        a = _mk("a-dangling", "open", "medium", ["ghost-never-existed"], "2026-01-02")
        x = _mk("x-dangling", "open", "medium", ["also-ghost"], "2026-01-01")
        full = [a, x]
        values = compute_values(full)
        full_by_title = {c.title: c for c in full}

        order = [
            c.title
            for c in sort_default(full, values=values, by_title=full_by_title)
        ]
        self.assertEqual(
            order,
            ["x-dangling", "a-dangling"],
            "dangling edges count 0 live flow, so the older card wins on age",
        )


if __name__ == "__main__":
    unittest.main()
