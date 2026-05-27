"""Regression test: read-time guards default to the UTC civil date.

Writes stamp dates in UTC (`_utc_now_iso`). The read-time guards
(`waiting_impedes`, `validate_waiting_overlay`, triage aging) must
default their `today` base to the SAME UTC calendar, not the local
civil date — otherwise, on a non-UTC runner near midnight, the two
disagree by a full day and a deferred card un-defers (or an overdue
wait surfaces / an age is computed) a civil day early.

The divergence only manifests at a specific wall-clock instant, so we
pin "now" to a UTC instant where the UTC and local (UTC+14) civil dates
differ, by monkeypatching the engine's `datetime`/`date` accessors. Then
we drive the DEFAULT path (no explicit `today=`) of `waiting_impedes`
and require it to match the UTC verdict. Before the fix the default was
`date.today()` (local) and the verdicts diverge -> exit 1. After the fix
the default is `_utc_today()` and they agree -> exit 0.

Run under the boundary TZ to exercise the skew:

    TZ=Pacific/Kiritimati uv run python <this file>
"""

import sys
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

import goc.engine as engine  # noqa: E402
from goc.engine import Card, waiting_impedes  # noqa: E402

# Pin a UTC instant where UTC date and a UTC+14 local date differ:
# 2026-05-26T12:00:00Z -> UTC date 2026-05-26, Kiritimati (UTC+14) 2026-05-27.
PINNED_UTC = datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
ts = PINNED_UTC.timestamp()

utc_today = datetime.fromtimestamp(ts, timezone.utc).date()
local_today = datetime.fromtimestamp(ts).astimezone().date()

print(f"pinned UTC instant : {PINNED_UTC.isoformat()}")
print(f"UTC civil date     : {utc_today}")
print(f"local civil date   : {local_today}")
print()

if utc_today == local_today:
    print("This runner's TZ does not skew the civil date at the pinned instant.")
    print("Run under TZ=Pacific/Kiritimati to exercise the boundary:")
    print("  TZ=Pacific/Kiritimati uv run python <this file>")
    sys.exit(0)


class _FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is not None:
            return PINNED_UTC.astimezone(tz)
        return datetime.fromtimestamp(ts)


class _FrozenDate(date):
    @classmethod
    def today(cls):
        return datetime.fromtimestamp(ts).date()


# Freeze the engine's clock at the pinned instant. `_utc_today()` reads
# `datetime.now(tz=timezone.utc).date()`; the buggy default read
# `date.today()` (local). Both now resolve to the pinned instant.
engine.datetime = _FrozenDateTime
engine.date = _FrozenDate

# A card deferred until the local civil date (one day ahead of UTC under
# UTC+14). At the pinned instant it is still 2026-05-26 in UTC, so the
# deferral (until 2026-05-27) is NOT elapsed -> the card must stay impeded.
# A local base, already at 2026-05-27, would treat it as elapsed and
# un-defer the card a full civil day early.
card = Card(
    title="demo",
    path=Path("/tmp/fake"),
    frontmatter={"title": "demo", "status": "open", "waiting_until": local_today.isoformat()},
    body="",
    dod_open=0,
    dod_done=0,
)

impeded_default = waiting_impedes(card)
impeded_utc = waiting_impedes(card, today=utc_today)
impeded_local = waiting_impedes(card, today=local_today)

print(f"waiting_impedes(card)                       = {impeded_default}  <- DEFAULT base")
print(f"waiting_impedes(card, today=UTC   {utc_today}) = {impeded_utc}")
print(f"waiting_impedes(card, today=local {local_today}) = {impeded_local}")
print()

if impeded_default != impeded_utc:
    print("DEFECT: the DEFAULT base diverges from the UTC base. The guard")
    print("un-defers a full civil day early on a non-UTC runner.")
    sys.exit(1)

print("PASS: the default base matches the UTC civil date; no local-tz drift.")
sys.exit(0)
