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


if __name__ == "__main__":
    unittest.main()
