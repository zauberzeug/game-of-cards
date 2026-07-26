"""A trailing newline must not slip through the ISO-date shape check.

Python's `$` anchor matches before a final newline, so a regex anchored
with `$` accepts "2026-08-01\n" — a value every full-value consumer
(`date.fromisoformat` in `_waiting_until_instant`, reached from
`goc validate` and `goc --waiting`) then rejects with a ValueError.
The predicate must reject what the parsers reject: `_is_iso_date` is
False for trailing-newline shapes, `_waiting_until_instant` returns its
None backstop instead of raising, and `validate_card` FAILs the stored
value instead of certifying it.

Regression test for the card
waiting-until-with-trailing-newline-passes-wait-then-crashes-reads.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import (  # noqa: E402
    Card,
    _is_iso_date,
    _waiting_until_instant,
    load_schema,
    validate_card,
    validate_waiting_overlay,
)


def _make_card(*, waiting_until) -> Card:
    fm = {
        "title": "test-card",
        "status": "open",
        "contribution": "medium",
        "human_gate": "none",
        "created": "2026-07-01T00:00:00Z",
        "waiting_on": "deferred",
        "waiting_until": waiting_until,
        "advances": [],
        "advanced_by": [],
        "tags": [],
        "definition_of_done": "- [ ] x",
    }
    return Card(
        title="test-card",
        path=Path("/dev/null"),
        frontmatter=fm,
        body="",
        dod_open=1,
        dod_done=0,
    )


class TrailingNewlineIsoDateTest(unittest.TestCase):
    def test_predicate_rejects_trailing_newline_date(self) -> None:
        self.assertFalse(_is_iso_date("2026-08-01\n"))

    def test_predicate_rejects_trailing_newline_datetime(self) -> None:
        self.assertFalse(_is_iso_date("2026-05-20T12:00:00Z\n"))

    def test_predicate_still_accepts_clean_shapes(self) -> None:
        self.assertTrue(_is_iso_date("2026-08-01"))
        self.assertTrue(_is_iso_date("2026-05-20T12:00:00Z"))

    def test_instant_parser_backstops_instead_of_raising(self) -> None:
        """`_waiting_until_instant` documents a None backstop for anything
        `_is_iso_date` rejects — the trailing-newline shape must take that
        path, not crash the read surfaces."""
        self.assertIsNone(_waiting_until_instant("2026-08-01\n"))

    def test_validate_card_fails_stored_trailing_newline(self) -> None:
        schema = load_schema()
        card = _make_card(waiting_until="2026-08-01\n")
        errors = validate_card(card, schema, {"test-card"})
        self.assertTrue(
            any("waiting_until" in e for e in errors),
            f"expected a waiting_until error, got {errors!r}",
        )

    def test_waiting_overlay_lint_does_not_crash(self) -> None:
        card = _make_card(waiting_until="2026-08-01\n")
        warnings = validate_waiting_overlay([card])
        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
