"""Demonstrate the UTC-write / local-read date-base mismatch.

Writes stamp dates in UTC (`_utc_now_iso`), but the read-time guards
(`waiting_impedes`, `validate_waiting_overlay`, triage aging) default
`today` to `date.today()` — the LOCAL civil date. On a non-UTC runner
near midnight the two disagree by a full day, so a card defers/un-defers
up to a civil day early.

This reproducer does not need to mock the wall clock: it pins one UTC
instant and derives the local-vs-UTC civil dates from it, then feeds
each into `waiting_impedes`. The bug is that the function's DEFAULT is
the local one; we prove the two bases give opposite verdicts and that
`date.today()` follows the local TZ (the buggy default).
"""

import os
import sys
import time
from datetime import datetime, timezone, date
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("repo root (pyproject.toml) not found")


sys.path.insert(0, str(_repo_root()))

# Pin a UTC instant where UTC date and a UTC+14 local date differ.
# 2026-05-26T12:00:00Z  ->  UTC date 2026-05-26, Kiritimati (UTC+14) date 2026-05-27.
PINNED_UTC = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
ts = PINNED_UTC.timestamp()

utc_today = datetime.fromtimestamp(ts, timezone.utc).date()
local_today = datetime.fromtimestamp(ts).astimezone().date()

print(f"pinned UTC instant : {PINNED_UTC.isoformat()}")
print(f"UTC civil date     : {utc_today}")
print(f"local civil date   : {local_today}  (TZ={os.environ.get('TZ', '<unset>')})")
print(f"date.today() now    : {date.today()}  <- the buggy default base")
print()

from goc.engine import Card, waiting_impedes  # noqa: E402

# A card deferred until 2026-05-27 (UTC). At the pinned UTC instant it is
# still 2026-05-26 in UTC, so the deferral is NOT yet elapsed -> impeded.
card = Card(
    title="demo",
    path=Path("/tmp/fake"),
    frontmatter={"title": "demo", "status": "open", "waiting_until": "2026-05-27"},
    body="",
    dod_open=0,
    dod_done=0,
)

impeded_utc = waiting_impedes(card, today=utc_today)
impeded_local = waiting_impedes(card, today=local_today)

print(f"waiting_impedes(card, today=UTC   {utc_today}) = {impeded_utc}")
print(f"waiting_impedes(card, today=local {local_today}) = {impeded_local}")
print()

if impeded_utc and not impeded_local:
    print("DEFECT CONFIRMED: under UTC+14 the card un-defers a full civil day")
    print("early. The correct (UTC) base still impedes; the local base (the")
    print("function's DEFAULT) does not.")
    sys.exit(1)

print("No divergence on this runner's TZ — run under TZ=Pacific/Kiritimati to")
print("exercise the boundary: TZ=Pacific/Kiritimati uv run python <this file>")
sys.exit(0)
