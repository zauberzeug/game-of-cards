"""Regression: render_json's `awaiting` / `dependency_awaiting` dependency
advisory must only render for live (non-terminal) cards.

Before the fix, `render_json` computed `dependency_blockers` /
`dependency_blocked` for every card regardless of its own status, so a
terminal card (done / disproved / superseded) that still carried a
non-terminal `advanced_by` prereq was reported with a non-empty
`awaiting` and `dependency_awaiting: true` — the "you may start" hint,
nonsensical on a card that cannot start, and a drift from the table /
board renderers, which gate the same signal behind
`status not in TERMINAL_STATUSES`. `ready` was already correct
(`card_is_ready` is open-only).
"""

from __future__ import annotations

import json
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


class JsonAwaitingLivenessTest(unittest.TestCase):
    def test_terminal_card_omits_advisory_live_card_keeps_it(self) -> None:
        prereq = _card("prereq-open", "open", [], "2026-06-18")
        live = _card("live-child", "open", ["prereq-open"], "2026-06-17")

        for terminal_status in ("done", "disproved", "superseded"):
            with self.subTest(status=terminal_status):
                closed = _card(
                    "closed-child", terminal_status, ["prereq-open"], "2026-06-17"
                )
                records = json.loads(
                    engine.render_json([closed, live, prereq])
                )
                by_title = {r["title"]: r for r in records}

                closed_rec = by_title["closed-child"]
                self.assertEqual(
                    closed_rec["awaiting"],
                    [],
                    msg=f"terminal ({terminal_status}) card leaked awaiting",
                )
                self.assertFalse(
                    closed_rec["dependency_awaiting"],
                    msg=f"terminal ({terminal_status}) card leaked "
                    "dependency_awaiting",
                )

                live_rec = by_title["live-child"]
                self.assertEqual(
                    live_rec["awaiting"],
                    ["prereq-open"],
                    msg="live card lost its awaiting advisory",
                )
                self.assertTrue(
                    live_rec["dependency_awaiting"],
                    msg="live card lost its dependency_awaiting flag",
                )


if __name__ == "__main__":
    unittest.main()
