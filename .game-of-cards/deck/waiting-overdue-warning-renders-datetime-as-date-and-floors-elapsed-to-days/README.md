---
title: waiting-overdue-warning-renders-datetime-as-date-and-floors-elapsed-to-days
summary: "`validate_waiting_overlay` decides overdue-ness at full datetime precision but renders the `WAITING_OVERDUE` warning with `until_dt.date().isoformat()` (drops the time) and `(now - until_dt).days` (floors sub-24h elapses to `0d`). A card deferred to `2026-05-30T23:00:00Z` checked at `2026-05-31T00:30:00Z` is reported as `waiting_until=2026-05-30 elapsed 0d ago` — the operator cannot see which datetime was stored, and the elapsed counter is `0d` for everything <24h overdue. The docstring promises full-timestamp parity with the read guard; the predicate keeps that promise but the rendered message breaks it."
status: done
stage: null
contribution: medium
created: "2026-05-30T11:51:09Z"
closed_at: "2026-05-30T12:34:01Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero and asserts the rendered `WAITING_OVERDUE` message echoes the stored timestamp shape (datetime when stored as datetime, date when stored as date) and shows sub-day elapse with hour granularity.
  - [x] TDD: the existing `WAITING_OVERDUE`-message tests still pass for the bare-date case (no regression on the date-only deferral display).
  - [x] MECHANICAL: `goc/engine.py` `validate_waiting_overlay` render at lines 1493-1498 stops calling `until_dt.date().isoformat()` and stops using `(now - until_dt).days` as the only elapsed precision.
  - [x] PROCESS: `uv run goc validate` passes; `uv run python -m unittest discover -s tests` passes.
  - [x] PROCESS: plugin mirrors re-synced by pre-commit; CI's `python scripts/sync_plugin_assets.py --check` stays green.
worker: {who: "claude[bot]", where: main}
---

# `WAITING_OVERDUE` warning renders datetime as date and floors elapsed to days

## Location

`goc/engine.py:1493-1498` (inside `validate_waiting_overlay`).

## What's broken

`validate_waiting_overlay` decides overdue-ness at full datetime
precision: `_waiting_until_instant` parses `YYYY-MM-DDTHH:MM:SSZ` at
seconds resolution, `_now_instant` keeps the comparison instant at
full precision, and the predicate at line 1490 is `until_dt > now`.
The docstring is explicit about the contract:

```python
# goc/engine.py:1469-1472
"""
The elapsed test uses the same full-timestamp comparison as
`waiting_impedes`: a datetime-form wait is not reported as overdue
until its named instant actually passes, so the read guard and this
validator agree on when a deferral has elapsed.
"""
```

But the *render* of the warning, four lines below the predicate,
throws that precision away:

```python
# goc/engine.py:1493-1498
warnings.append(BlockerWarning(
    "WAITING_OVERDUE",
    c.title,
    f"waiting_on={reason} waiting_until={until_dt.date().isoformat()} "
    f"elapsed {(now - until_dt).days}d ago — re-triage or clear",
))
```

Two precision drops in one f-string:

1. `until_dt.date().isoformat()` discards the time component. A card
   that stored `waiting_until: 2026-05-30T23:00:00Z` is reported as
   `waiting_until=2026-05-30`. The operator cannot tell from the
   warning whether the stored value was a bare date or a datetime,
   and cannot see the *instant* the deferral was supposed to clear.
2. `(now - until_dt).days` is `timedelta.days`, which is the integer
   floor in days. A datetime-form deferral that elapsed 30 minutes
   ago reports `elapsed 0d ago`. So does one that elapsed 23 hours
   ago. Everything `[0, 1)` days overdue is collapsed into the same
   `0d ago` rendering — exactly the precision range a datetime-form
   `waiting_until` was added to express.

The predicate honors the contract; the message immediately rounds it
back down to the legacy date-only resolution. The validator output
*is* the SLE-escalation channel — it's what the human reads to
decide whether a wait has genuinely overrun or just rolled over
midnight. Rounding the rendered value silently re-introduces the
ambiguity datetime-form `waiting_until` was added to remove.

## Reachability

The render path is exercised any time `validate_waiting_overlay` runs
against a non-terminal card with an elapsed `waiting_until` that is
a datetime. The schema accepts both shapes (`_is_iso_date` at
`engine.py:687-711` admits date and datetime), `_waiting_until_instant`
parses both (`engine.py:730-757`), and cards in this repo's own deck
already carry `waiting_on: external` overlays. The `_now_instant` /
`_waiting_until_instant` work — and the docstring at 1469-1472
explicitly defending the time component — were the most recent
changes in this area, which makes the rendered-message drift the
relevant gap: the comparator was fixed, the renderer was not.

## Empirical evidence

`reproduce.py` constructs a non-terminal card with
`waiting_until = "2026-05-30T23:00:00Z"` and a comparison instant of
`2026-05-31T00:30:00Z` (30 minutes after the deferral elapsed). The
predicate fires (good — that part of the contract is kept), but the
rendered message shows `waiting_until=2026-05-30 elapsed 0d ago`:

```text
WAIT actually elapsed: 1h30m  (0.0625 days)
predicate fires?      : True
rendered warning      : 'WARN WAITING_OVERDUE test-card: waiting_on=external waiting_until=2026-05-30 elapsed 0d ago — re-triage or clear'
contains stored time? : False
shows fractional day? : False
```

Run the reproducer with `uv run python deck/waiting-overdue-warning-renders-datetime-as-date-and-floors-elapsed-to-days/reproduce.py`.

## Why it matters

The validator output is what the operator reads to triage stuck
work. Two failure modes follow from the precision drop:

- A card deferred to `2026-05-30T23:00:00Z` and checked the morning
  after looks indistinguishable from one deferred to a bare
  `2026-05-30` and checked the morning after. The whole point of
  the datetime form is that operators can tell those apart; the
  warning erases that.
- A card that elapsed 23 hours ago and one that elapsed 30 minutes
  ago both report `0d ago`. Anyone draining the impediment queue
  cannot distinguish "just expired, give it another hour" from
  "should have been retriaged yesterday."

The companion read-time guard (`waiting_impedes` at `engine.py:1758`)
is correct at full precision. The mismatch is purely in the human-
facing rendering of the same condition.

## Fix

Replace the message construction in `validate_waiting_overlay` to
echo the stored timestamp shape and render elapsed time with sub-day
granularity. Sketch:

```python
def _format_waiting_until_for_message(value, until_dt: datetime) -> str:
    # Echo the stored shape: bare date stays bare; datetime keeps its instant.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s = str(value)
    return s


def _format_elapsed(delta: timedelta) -> str:
    total = int(delta.total_seconds())
    if total < 3600:
        return f"{total // 60}m"
    if total < 86400:
        return f"{total // 3600}h"
    return f"{total // 86400}d"
```

Then in `validate_waiting_overlay`:

```python
warnings.append(BlockerWarning(
    "WAITING_OVERDUE",
    c.title,
    f"waiting_on={reason} waiting_until={_format_waiting_until_for_message(until, until_dt)} "
    f"elapsed {_format_elapsed(now - until_dt)} ago — re-triage or clear",
))
```

The bare-date input shape stays rendered as `YYYY-MM-DD` (no
regression for existing tests); the datetime input shape stays
rendered as its stored UTC instant; sub-day elapses render in
hours/minutes instead of collapsing to `0d`.

The exact helper signatures are illustrative — what the fix MUST
preserve is the contract the docstring at lines 1469-1472 promises:
the validator's output and the read guard's verdict agree, *all the
way through to the rendered message the operator reads*.
