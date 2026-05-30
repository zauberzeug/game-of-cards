"""WAITING_OVERDUE warning preserves the stored timestamp shape and renders
sub-day elapses at hour/minute granularity.

`validate_waiting_overlay` decides overdue-ness at full datetime precision
(its docstring explicitly defends the read-guard parity). The rendered
warning string must agree: a datetime-form `waiting_until` keeps its time
component in the message, and an elapse under 24 hours renders with
hour/minute precision instead of `0d ago`. A bare-date `waiting_until`
stays rendered as `YYYY-MM-DD` (no regression on the legacy shape).
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from goc.engine import Card, validate_waiting_overlay  # noqa: E402


def _make_card(*, waiting_until, waiting_on: str = "external") -> Card:
    fm = {
        "title": "test-card",
        "status": "open",
        "contribution": "medium",
        "human_gate": "none",
        "waiting_on": waiting_on,
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


class WaitingOverdueMessageTest(unittest.TestCase):
    def test_datetime_waiting_until_echoes_full_instant(self) -> None:
        """A datetime-form `waiting_until` must keep its time component in the
        rendered message — the read guard honors the instant, the validator's
        operator-facing output must echo the same instant."""
        until_str = "2026-05-30T23:00:00Z"
        now = datetime(2026, 5, 31, 0, 30, tzinfo=timezone.utc)
        card = _make_card(waiting_until=until_str)

        warnings = validate_waiting_overlay([card], today=now)
        self.assertEqual(1, len(warnings))
        msg = warnings[0].message

        self.assertIn(
            "waiting_until=2026-05-30T23:00:00Z",
            msg,
            f"datetime-form waiting_until lost its time component: {msg!r}",
        )

    def test_sub_day_elapse_renders_in_hours_not_zero_days(self) -> None:
        """An elapse under 24 hours must NOT render as `0d ago` — the operator
        needs to distinguish "just expired" from "long overdue."""
        until_str = "2026-05-30T23:00:00Z"
        now = datetime(2026, 5, 31, 0, 30, tzinfo=timezone.utc)
        card = _make_card(waiting_until=until_str)

        warnings = validate_waiting_overlay([card], today=now)
        msg = warnings[0].message

        self.assertNotIn(
            "0d ago",
            msg,
            f"sub-day elapse collapsed to '0d ago': {msg!r}",
        )
        self.assertIn(
            "1h ago",
            msg,
            f"1h30m elapse should render as '1h ago': {msg!r}",
        )

    def test_sub_hour_elapse_renders_in_minutes(self) -> None:
        """An elapse under one hour renders with minute granularity."""
        until_str = "2026-05-30T23:00:00Z"
        now = datetime(2026, 5, 30, 23, 15, tzinfo=timezone.utc)
        card = _make_card(waiting_until=until_str)

        warnings = validate_waiting_overlay([card], today=now)
        msg = warnings[0].message

        self.assertIn(
            "15m ago",
            msg,
            f"15-minute elapse should render in minutes: {msg!r}",
        )

    def test_multi_day_elapse_still_renders_in_days(self) -> None:
        """An elapse ≥24h continues to render in days — no regression on the
        existing multi-day case."""
        now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
        card = _make_card(waiting_until="2026-05-28T12:00:00Z")

        warnings = validate_waiting_overlay([card], today=now)
        msg = warnings[0].message

        self.assertIn(
            "3d ago",
            msg,
            f"3-day elapse should render as '3d ago': {msg!r}",
        )

    def test_bare_date_waiting_until_stays_date_only(self) -> None:
        """The legacy bare-date shape must continue to render as `YYYY-MM-DD`
        (no spurious `T00:00:00Z` suffix on a date-only input)."""
        now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
        card = _make_card(waiting_until=date(2026, 5, 28))

        warnings = validate_waiting_overlay([card], today=now)
        msg = warnings[0].message

        self.assertIn(
            "waiting_until=2026-05-28",
            msg,
            f"bare-date waiting_until should stay date-only: {msg!r}",
        )
        self.assertNotIn(
            "2026-05-28T",
            msg,
            f"bare-date waiting_until must not gain a time component: {msg!r}",
        )

    def test_bare_date_string_waiting_until_stays_date_only(self) -> None:
        """A bare-date string (the legacy shape before datetime support) stays
        rendered as `YYYY-MM-DD`."""
        now = datetime(2026, 5, 31, 12, 0, tzinfo=timezone.utc)
        card = _make_card(waiting_until="2026-05-28")

        warnings = validate_waiting_overlay([card], today=now)
        msg = warnings[0].message

        self.assertIn("waiting_until=2026-05-28", msg)
        self.assertNotIn("2026-05-28T", msg)


if __name__ == "__main__":
    unittest.main()
