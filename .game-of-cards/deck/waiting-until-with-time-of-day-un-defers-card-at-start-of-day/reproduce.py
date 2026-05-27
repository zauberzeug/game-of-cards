"""Proof: a datetime-form `waiting_until` un-defers the card at the START of
its civil day, ignoring the time component — releasing it up to ~24h early.

The engine accepts the `YYYY-MM-DDTHH:MM:SSZ` shape for `waiting_until`
(via `_is_iso_date` / the `goc wait --until` validator), but `waiting_impedes`
truncates it to a bare date with `_date_part` and compares `until_date > today`.
So a card deferred until `2026-05-27T23:59:59Z` is treated as un-impeded the
entire civil day 2026-05-27 — it re-enters the pull/ready queue ~24h early.

Run: uv run python deck/<title>/reproduce.py
Exit 0 == the bug is FIXED (end-of-day wait still impedes at start-of-day).
Exit 1 == the bug reproduces.
"""

import sys
from datetime import date, datetime, timezone
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

from goc.engine import Card, validate_waiting_overlay, waiting_impedes  # noqa: E402


def _card(waiting_until: str) -> Card:
    # Minimal Card carrying only the impediment overlay we care about.
    return Card(
        title="repro",
        path=Path("/tmp/repro"),
        frontmatter={
            "status": "open",
            "contribution": "medium",
            "human_gate": "none",
            "waiting_until": waiting_until,
        },
        body="",
        dod_open=0,
        dod_done=0,
    )


def main() -> int:
    today = date(2026, 5, 27)

    # End-of-day on the civil day the card is being evaluated.
    end_of_day = _card("2026-05-27T23:59:59Z")
    impedes_eod = waiting_impedes(end_of_day, today=today)

    # A bare date for the SAME civil day (legacy date-only form) — this one
    # SHOULD un-defer at the start of the day; we keep it as the baseline.
    bare_today = _card("2026-05-27")
    impedes_bare = waiting_impedes(bare_today, today=today)

    print(f"today (UTC civil)                 = {today.isoformat()}")
    print(f"waiting_until 2026-05-27T23:59:59Z -> impedes = {impedes_eod}  (want True)")
    print(f"waiting_until 2026-05-27 (bare)    -> impedes = {impedes_bare}  (want False)")
    print()

    now = datetime(2026, 5, 27, 8, 0, 0, tzinfo=timezone.utc)
    print(f"At wall-clock {now.isoformat()} the end-of-day wait has NOT elapsed,")
    print("so the card should still be impeded (hidden from the ready queue).")
    print()

    # validate_waiting_overlay must use the same full-timestamp comparison:
    # an end-of-day datetime wait is NOT yet elapsed at the start of its day,
    # so it must not be surfaced as WAITING_OVERDUE.
    overdue_titles = {
        w.card for w in validate_waiting_overlay([end_of_day], today=today)
    }
    eod_flagged_early = "repro" in overdue_titles
    print(f"validate_waiting_overlay(end-of-day) overdue = {eod_flagged_early}  (want False)")

    # A datetime that genuinely elapsed before `today` SHOULD still surface.
    past = _card("2026-05-25T12:00:00Z")
    past_overdue = {w.card for w in validate_waiting_overlay([past], today=today)}
    past_flagged = "repro" in past_overdue
    print(f"validate_waiting_overlay(elapsed)    overdue = {past_flagged}  (want True)")
    print()

    if impedes_eod and not eod_flagged_early and past_flagged:
        print("PASS: end-of-day datetime wait still impedes and is not flagged overdue early.")
        return 0

    print("FAIL: end-of-day datetime wait un-defers ~16h early — time component dropped.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
