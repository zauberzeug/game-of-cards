"""Regression: walkers must treat a non-list `advances`/`advanced_by`
frontmatter value as an empty edge set, matching `find_half_edges` and
`validate_card`.

A hand-edited bare-string scalar (e.g. `advances: bcard`) used to be
iterated character-by-character by `compute_values` and the cycle
detectors — emitting phantom dangling-edge warnings on the render path
and inflating priority values via a chance self-match on the
in-progress cycle branch.
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr

from goc import engine


def _card(title: str, contribution: str = "low", **fm_extra) -> engine.Card:
    fm = {
        "title": title,
        "status": "open",
        "contribution": contribution,
        "advances": [],
        "advanced_by": [],
    }
    fm.update(fm_extra)
    return engine.Card(
        title=title, path=None, frontmatter=fm, body="", dod_open=0, dod_done=0
    )


class NonListAdvancesGuardTest(unittest.TestCase):
    def setUp(self) -> None:
        engine._DANGLING_ADVANCES_WARNED.clear()

    def test_compute_values_treats_bare_string_advances_as_empty(self) -> None:
        """The render path is not gated by `goc validate`, so a hand-edited
        bare-string `advances` must not be walked character-by-character."""
        card = _card("a", advances="bcard")
        own = engine.CONTRIBUTION_RANK["low"]

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            values = engine.compute_values([card])
        value, path = values["a"]

        self.assertEqual(value, own, "leaf with non-list advances should value at own rank")
        self.assertEqual(path, ["self"])
        self.assertNotIn("dangling advances edge", stderr.getvalue())

    def test_compute_values_treats_other_non_list_advances_as_empty(self) -> None:
        for bad in (None, "string", 42, {"not": "a list"}):
            with self.subTest(bad=bad):
                engine._DANGLING_ADVANCES_WARNED.clear()
                card = _card("a", advances=bad)
                own = engine.CONTRIBUTION_RANK["low"]
                stderr = io.StringIO()
                with redirect_stderr(stderr):
                    values = engine.compute_values([card])
                value, _ = values["a"]
                self.assertEqual(value, own)
                self.assertNotIn("dangling advances edge", stderr.getvalue())

    def test_detect_advance_cycles_ignores_non_list_advanced_by(self) -> None:
        # Bare-string `advanced_by` must not crash or emit a spurious cycle.
        card = _card("a", advanced_by="abc")
        errors = engine.detect_advance_cycles([card])
        self.assertEqual(errors, [])

    def test_would_create_advance_cycle_ignores_non_list_advances(self) -> None:
        # _would_create_advance_cycle walks `advances` from a starting card;
        # a bare-string value must be treated as no outgoing edges.
        a = _card("a", advances="bcard")
        b = _card("b")
        self.assertFalse(engine._would_create_advance_cycle([a, b], "a", "b"))

    def test_find_half_edges_treats_non_list_inverse_as_empty(self) -> None:
        # `find_half_edges` walks the neighbour's inverse field after the
        # outer guard; a bare-string inverse must not fall back to Python's
        # substring `in` (which silently affirms a reverse edge that does
        # not structurally exist).
        a = _card("acard", advances=["bcard"])
        b = _card("bcard", advanced_by="acard-suffix-that-contains-acard")
        edges = engine.find_half_edges([a, b])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].src, "acard")
        self.assertEqual(edges[0].field, "advances")
        self.assertEqual(edges[0].ref, "bcard")
        self.assertEqual(edges[0].inverse, "advanced_by")

    def test_find_half_edges_treats_exact_match_bare_string_as_empty(self) -> None:
        # Even an exact-match bare string is not a list; the structural
        # invariant requires the inverse to be a list, not a scalar.
        a = _card("acard", advances=["bcard"])
        b = _card("bcard", advanced_by="acard")
        edges = engine.find_half_edges([a, b])
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].ref, "bcard")


if __name__ == "__main__":
    unittest.main()
