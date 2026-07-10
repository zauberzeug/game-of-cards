---
title: set-cadence-day-interval-over-31-emits-monthly-only-cron
status: done
stage: null
contribution: low
created: "2026-06-22T09:01:11Z"
closed_at: "2026-06-22T09:03:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
summary: |
  interval_to_cron in scripts/set_cadence.py guards only the lower bound
  of an N-day interval. For N > 31 it emits a `*/N` step into cron's
  day-of-month field (max 31), which can only ever match day 1 — silently
  collapsing "every N days" into "monthly on the 1st" with no error.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (interval_to_cron raises ValueError for an N-day spec with N > 31 instead of returning a never-fires-as-asked cron)
  - [x] TDD: tests/test_set_cadence.py gains a case asserting ValueError for N > 31 (e.g. "40d"), and asserts the valid boundary "31d" still translates
  - [x] MECHANICAL: the day path's guard mirrors the hour path's reject-out-of-range pattern, with an error message naming cron's day-of-month max
worker: {who: "claude[bot]", where: main}
---

# set-cadence-day-interval-over-31-emits-monthly-only-cron

> Later evidence: the N > 31 boundary this card shipped is off by one — a
> `*/31` step also enumerates only day 1 (`1 + 31 = 32 > 31`), so `31d`
> collapses to monthly exactly like the `*/40` case rejected here. Fixed by
> [set-cadence-accepts-31d-which-collapses-to-monthly-only-cron](../set-cadence-accepts-31d-which-collapses-to-monthly-only-cron/),
> which tightened the guard to N <= 30 and superseded this card's
> "31d still translates" DoD assertion.

## Location

`scripts/set_cadence.py:84-90` — the `unit == "d"` branch of `interval_to_cron`.

## What's broken

The day-interval path validates only the lower bound and then emits a
`*/N` step straight into cron's **day-of-month** field:

```python
if unit == "d":
    if n < 1:
        raise ValueError(f"{spec!r}: day interval must be >= 1")
    if n == 1:
        return f"{offset} 0 * * *"
    # day-of-month */N: roughly every N days, realigning each month.
    return f"{offset} 0 */{n} * *"
```

cron's day-of-month field ranges 1–31. A step `*/N` enumerates `1, 1+N,
1+2N, …` and drops everything above 31. For any `N > 31`, the only
candidate that survives is day 1 (`1 + N > 31` always), so the cron
fires **once a month on the 1st** regardless of how large N is —
"every 40 days" and "every 365 days" both become "monthly on the 1st."
No error is raised; the misconfiguration is silent.

The asymmetry is the tell: the hour path one branch below explicitly
rejects out-of-range steps —

```python
if not 1 <= n <= 23 or 24 % n != 0:
    raise ValueError(
        f"{spec!r}: hour interval must divide 24 (1,2,3,4,6,8,12) or be 24h"
    )
```

— but the day path has no corresponding upper-bound guard. The
docstring documents the month-boundary *realignment* caveat for
`Nd` (N≥2) but says nothing about the N>31 collapse.

## Empirical evidence

`reproduce.py` on a clean checkout (defect present):

```
interval_to_cron('40d', 15) returned '15 0 */40 * *'
  -> fires on days-of-month: [1]
FAIL: a 40-day interval collapsed to 'monthly on the 1st' with no error.
      cron's day-of-month field caps at 31; */40 can only match day 1.
```

The `*/40` day-of-month step matches only day 1, so the requested
"every 40 days" cadence silently becomes "monthly on the 1st."

## Why it matters

`scripts/set_cadence.py` is the repo-local cadence tool (wrapped by the
`tune-cadence` skill). `retune()` writes whatever `interval_to_cron`
returns directly into `.github/workflows/<workflow>.yml` as a `- cron:`
line. A maintainer who runs `set_cadence.py --refine 40d` intending
"every 40 days" gets a workflow that silently fires monthly-on-the-1st
instead — a cadence that does not match the request and gives no
feedback that the spec was unrepresentable. The reachable invocation is
`python3 scripts/set_cadence.py --<workflow> Nd` for any N > 31.

## Fix (applied)

Added an upper-bound guard to the day path mirroring the hour path's
reject-out-of-range behavior — cron's day-of-month field caps at 31, so
a step larger than that cannot approximate "every N days":

```python
if unit == "d":
    if n < 1:
        raise ValueError(f"{spec!r}: day interval must be >= 1")
    if n > 31:
        raise ValueError(
            f"{spec!r}: day interval must be <= 31 "
            "(cron's day-of-month field caps at 31; a larger step fires "
            "only on the 1st)"
        )
    if n == 1:
        return f"{offset} 0 * * *"
    # day-of-month */N: roughly every N days, realigning each month.
    return f"{offset} 0 */{n} * *"
```

`31d` stays valid (it already collapses toward monthly via the
documented realignment caveat — that is the existing, intended
boundary behavior); only `N > 31`, which can never represent the
requested cadence, is rejected.
