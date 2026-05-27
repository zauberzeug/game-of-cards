---
title: read-time-date-guards-compare-utc-stamps-to-local-date
summary: "Cards stamp dates in UTC (`_utc_now_iso`) but three read-time guards — `waiting_impedes`, `validate_waiting_overlay`, and triage aging — default `today` to `date.today()` (the LOCAL civil date). On a non-UTC runner near midnight the two bases disagree by a full day, so a deferred card un-defers (or an overdue wait surfaces, or an age is computed) up to one civil day early. Contradicts the closed `record-card-timestamps-as-utc-datetime` card's audit claim of \"UTC-only enforced (no local-tz drift)\"."
status: done
stage: null
contribution: medium
created: "2026-05-27T02:27:59Z"
closed_at: 2026-05-27T02:33:48Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero (the chosen `today` base no longer
        diverges from the write-side UTC base under `TZ=Pacific/Kiritimati`).
  - [x] MECHANICAL: the three read-time `today = ... or date.today()` /
        `today = date.today()` defaults (engine.py `waiting_impedes`,
        `validate_waiting_overlay`, `_cmd_triage` `aged_days`) derive
        from the same UTC base the write side uses (a `_utc_today()`
        helper paired with `_utc_now_iso`), keeping the injectable
        `today=` test parameter.
  - [x] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) and `uv run goc validate` clean.
  - [x] PROCESS: the closed `record-card-timestamps-as-utc-datetime` card gets a dated `log.md` forward-pointer noting the read-side gap its audit missed.
worker: {who: "claude[bot]", where: main}
---

# Read-time date guards compare UTC-stamped dates against the local civil date

The write side stamps every date in UTC; three read-time guards compare
those stamps against `date.today()`, which is the **local** civil date.
On a runner whose timezone is not UTC, the two bases disagree by up to a
full day around midnight, so deferral / overdue / aging decisions fire a
civil day early or late.

## Location

- `goc/engine.py:1651` — `waiting_impedes`: `today = today or date.today()`,
  then `return until_date > today`. Decides whether a deferred card is
  hidden from the ready queue.
- `goc/engine.py:1366` — `validate_waiting_overlay`: `today = today or date.today()`,
  then `if until_date >= today: continue`. Decides the `WAITING_OVERDUE`
  SLE-escalation signal.
- `goc/engine.py:4173` — `_cmd_triage` `aged_days`: `today = date.today()`,
  then `(today - created).days`. The parked-card age shown in `goc triage`.

## What's broken

Every WRITE site uses UTC:

```python
# goc/engine.py:684
def _utc_now_iso() -> str:
    ...
# used at 2903, 3400, 3563, 3693, 4101, 4126 — created/closed_at stamps
```

But the READ-time comparisons above default to the local civil date:

```python
# goc/engine.py:1651 (waiting_impedes)
today = today or date.today()
...
return until_date > today
```

`date.today()` is `datetime.now().date()` — local time. A `waiting_until`
written/intended on the UTC calendar is therefore compared against a
date that, near midnight on a non-UTC runner, is off by one.

This contradicts the audit claim recorded when UTC stamping landed:

> **Audit**: PASS — ... UTC-only enforced (no local-tz drift); ...
> (`.game-of-cards/deck/record-card-timestamps-as-utc-datetime/log.md:9`)

That audit covered only the write side plus lexicographic sort / `--since`
reads; the read-time `date.today()` comparisons were never converted, so
the "no local-tz drift" guarantee has a hole.

## Empirical evidence

`reproduce.py` pins one UTC instant (`2026-05-26T12:00:00Z`) where the UTC
civil date is `2026-05-26` but the `Pacific/Kiritimati` (UTC+14) civil date
is already `2026-05-27`, then evaluates a card deferred until `2026-05-27`:

```
pinned UTC instant : 2026-05-26T12:00:00+00:00
UTC civil date     : 2026-05-26
local civil date   : 2026-05-27  (TZ=Pacific/Kiritimati)
date.today() now    : 2026-05-27  <- the buggy default base

waiting_impedes(card, today=UTC   2026-05-26) = True
waiting_impedes(card, today=local 2026-05-27) = False

DEFECT CONFIRMED: under UTC+14 the card un-defers a full civil day
early. The correct (UTC) base still impedes; the local base (the
function's DEFAULT) does not.
```

By the UTC calendar the deferral is still active (it is `2026-05-26`),
but the local-date default un-defers the card a full civil day early.
The same one-day skew applies symmetrically to `WAITING_OVERDUE`
escalation and to triage `aged_days`.

## Why it matters

Deferral is the one mechanism designed to make a card *invisible* until a
date. A guard that fires a day early defeats the purpose silently — the
card reappears in `goc --ready` (and the autonomous pull queue) before the
deferral elapses, with no log of why. Bounded to ≤1 civil day and only on
non-UTC runners near midnight, but it is an undocumented contract gap and
the whole point of UTC stamping was to remove timezone-dependent behavior.

## Fix

Add a `_utc_today()` helper next to `_utc_now_iso` (engine.py:684) that
returns `datetime.now(timezone.utc).date()`, and make the three guards
default to it instead of `date.today()`:

```python
def _utc_today() -> date:
    return datetime.now(timezone.utc).date()
```

```python
# waiting_impedes / validate_waiting_overlay
today = today or _utc_today()
# _cmd_triage
today = _utc_today()
```

Keep the injectable `today=` parameter on `waiting_impedes` /
`validate_waiting_overlay` (used by tests); only the *default* changes.
Re-sync plugin mirrors and add the forward-pointer to the closed UTC card.
