"""Regression: the `goc validate` cycle gate and the edge-add guard must
read the same edge field.

`detect_advance_cycles` (the gate) walked `advanced_by` while
`_would_create_advance_cycle` (the guard `goc advance`, `goc new` and
`goc repair-edges` consult) walks `advances`. The fields mirror each other
only on a deck without half-edges, so on a half-edged deck the two reached
opposite verdicts about one cycle: a cycle recorded only in `advances` went
unreported by the gate while the guard refused to extend it, and the
reverse. Both now walk `advances`, the field the `compute_values` priority
walk reads.
"""
from __future__ import annotations

import unittest

from goc import engine

CYCLE = (("a", "b"), ("b", "c"), ("c", "a"))
CHAIN = (("a", "b"), ("b", "c"))


def _deck(edges, *, advances: bool, advanced_by: bool) -> list[engine.Card]:
    """Three cards whose `parent → child` edges are recorded in the chosen fields."""
    fm = {t: {"title": t, "status": "open", "advances": [], "advanced_by": []} for t in "abc"}
    for parent, child in edges:
        if advances:
            fm[parent]["advances"].append(child)
        if advanced_by:
            fm[child]["advanced_by"].append(parent)
    return [
        engine.Card(title=t, path=None, frontmatter=fm[t], body="", dod_open=0, dod_done=0)
        for t in "abc"
    ]


def _verdicts(edges, **fields) -> tuple[bool, bool]:
    """(gate reports a cycle, guard refuses one of the deck's own edges)."""
    cards = _deck(edges, **fields)
    gate = bool(engine.detect_advance_cycles(cards))
    guard = any(engine._would_create_advance_cycle(cards, child, parent) for parent, child in edges)
    return gate, guard


class AdvanceCycleWalkersAgreeTest(unittest.TestCase):
    def test_cycle_recorded_only_in_advances_is_seen_by_both(self) -> None:
        # The card's recipe: before the fix the gate returned [] here while
        # the guard refused every edge of the cycle.
        self.assertEqual(_verdicts(CYCLE, advances=True, advanced_by=False), (True, True))

    def test_cycle_recorded_only_in_advanced_by_gets_one_verdict(self) -> None:
        # The mirror: before the fix the gate reported this cycle while the
        # guard let `goc advance` extend it. The walkers read one field, and
        # the half-edges here fail validation on their own.
        gate, guard = _verdicts(CYCLE, advances=False, advanced_by=True)
        self.assertEqual(gate, guard)

    def test_cycle_in_both_fields_is_seen_by_both(self) -> None:
        # Control: the shape a half-edge-free deck carries.
        self.assertEqual(_verdicts(CYCLE, advances=True, advanced_by=True), (True, True))

    def test_acyclic_chain_is_seen_by_neither(self) -> None:
        self.assertEqual(_verdicts(CHAIN, advances=True, advanced_by=True), (False, False))

    def test_cycle_error_names_the_field_it_walked(self) -> None:
        cards = _deck(CYCLE, advances=True, advanced_by=False)
        errors = engine.detect_advance_cycles(cards)
        self.assertIn("a: advances: cycle detected through c → a", errors)
        self.assertFalse([e for e in errors if "advanced_by" in e], errors)


if __name__ == "__main__":
    unittest.main()
