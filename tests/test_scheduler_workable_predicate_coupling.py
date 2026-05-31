"""Regression: `card_is_workable_for_scheduler` stays coupled to `card_is_ready`.

The scheduler descendant-prune in `compute_values.value_for` and
`sort_default.live_direct` mirror every rejection axis of `card_is_ready`
EXCEPT the `status == "open"` clause — `active` descendants stay workable
because the scheduler walks live work, not just queueable work.

This test fails loudly if a future axis is added to `card_is_ready`
without being mirrored into `card_is_workable_for_scheduler` (or vice
versa). It introspects both predicates across the cross-product of
`status × human_gate × waiting_on` documented in the card body and
asserts agreement modulo the `active`-allowed clause.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from goc.engine import (
    Card,
    card_is_ready,
    card_is_workable_for_scheduler,
)


def _mk(
    *,
    status: str,
    human_gate: str,
    waiting_on: str | None,
) -> Card:
    fm: dict = {
        "title": "C",
        "status": status,
        "contribution": "medium",
        "human_gate": human_gate,
        "advances": [],
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [ ] X\n",
    }
    if waiting_on is not None:
        fm["waiting_on"] = waiting_on
    return Card(
        title="C",
        path=Path("/tmp/C"),
        frontmatter=fm,
        body="",
        dod_open=1,
        dod_done=0,
    )


STATUSES = ("open", "active", "done", "disproved", "superseded")
GATES = ("none", "decision", "session")
WAITING = (None, "external", "resource", "deferred")


class SchedulerWorkablePredicateCouplingTest(unittest.TestCase):
    def test_helper_matches_card_is_ready_except_for_active_status(self) -> None:
        for status in STATUSES:
            for gate in GATES:
                for waiting in WAITING:
                    card = _mk(status=status, human_gate=gate, waiting_on=waiting)
                    ready = card_is_ready(card, {card.title: card})
                    workable = card_is_workable_for_scheduler(card)
                    with self.subTest(status=status, gate=gate, waiting=waiting):
                        if status == "active" and gate == "none" and waiting is None:
                            # The only documented divergence: the helper
                            # accepts `active` (live work amplifies value)
                            # while `card_is_ready` rejects it (cannot be
                            # pulled — already claimed).
                            self.assertFalse(ready)
                            self.assertTrue(workable)
                        else:
                            self.assertEqual(
                                ready,
                                workable,
                                f"predicate drift at status={status!r} "
                                f"gate={gate!r} waiting={waiting!r}: "
                                f"card_is_ready={ready} "
                                f"card_is_workable_for_scheduler={workable}",
                            )


if __name__ == "__main__":
    unittest.main()
