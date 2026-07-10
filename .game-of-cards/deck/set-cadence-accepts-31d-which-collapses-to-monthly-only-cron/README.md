---
title: set-cadence-accepts-31d-which-collapses-to-monthly-only-cron
summary: "interval_to_cron's day-interval upper bound is off by one: the guard rejects N > 31, but a */31 day-of-month step enumerates days {1, 32} and therefore also matches only the 1st — the exact silent monthly collapse the guard's own error message says it rejects. 30d (days {1, 31}) is the real last representable step; 31d must be rejected too."
status: done
stage: null
contribution: low
created: "2026-07-09T01:36:08Z"
closed_at: "2026-07-09T01:43:43Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (interval_to_cron raises ValueError for "31d" instead of returning a cron whose day-of-month step matches only day 1)
  - [x] TDD: tests/test_set_cadence.py boundary cases updated — "31d" rejected, "30d" asserted as the last supported day step
  - [x] MECHANICAL: docstring and error message state the 1 ≤ N ≤ 30 range with the day-1-collapse rationale
worker: {who: "claude[bot]", where: main}
---

# set-cadence accepts `31d`, which collapses to the monthly-only cron its own guard rejects

## Location

`scripts/set_cadence.py:100-109` — the `unit == "d"` upper-bound guard and
step emission in `interval_to_cron`.

## What's broken

The guard added by the predecessor card
[set-cadence-day-interval-over-31-emits-monthly-only-cron](../set-cadence-day-interval-over-31-emits-monthly-only-cron/)
rejects only `N > 31`:

```python
        if n > 31:
            raise ValueError(
                f"{spec!r}: day interval must be <= 31 "
                "(cron's day-of-month field caps at 31; a larger */N step "
                "fires only on the 1st)"
            )
        ...
        return f"{offset} 0 */{n} * *"
```

But a `*/N` day-of-month step enumerates `1, 1+N, 1+2N, …` capped at 31, and
`1 + 31 = 32 > 31` — so `*/31` matches **only day 1**, identically to the
`*/40` case the guard was written to reject. The predecessor card's own
analysis states the collapse condition in a form that includes 31 ("for any
`N > 31`, the only candidate that survives is day 1 (`1 + N > 31` always)" —
true for N = 31 as well), yet its DoD blessed the wrong boundary ("asserts
the valid boundary \"31d\" still translates"), and
`tests/test_set_cadence.py:87-89` codifies it with a false comment:

```python
    def test_day_interval_boundary_31_supported(self) -> None:
        # 31d is the last representable day-of-month step.
        self.assertEqual(setc.interval_to_cron("31d", 0), "0 0 */31 * *")
```

`*/30` (days {1, 31}) is the actual last step with more than one candidate
day; the docstring's "1 ≤ N ≤ 31" range and the error message's "must be
<= 31" repeat the off-by-one.

## Why it matters

Reachability: `python3 scripts/set_cadence.py --pull 31d` (or the
`tune-cadence` skill on "run pull-card every 31 days") silently retunes
`.github/workflows/pull-card.yml` to first-of-month-only — the precise
silent misconfiguration the predecessor card classified as a defect worth a
ValueError. The guard's rationale text and its boundary disagree; one of
them is wrong, and the arithmetic says it's the boundary.

## Decision (rubric-derived)

- **Choice:** tighten the guard to reject N = 31 as well (`if n > 30`),
  making `30d` the documented maximum.
- **Principle invoked:** the predecessor card's recorded rationale — an
  every-N-days spec whose emitted `*/N` step can only ever match day 1 is a
  silent monthly collapse and must raise ValueError rather than emit a cron
  that "never fires as asked." N = 31 satisfies that condition
  (`1 + 31 > 31`). The hour path's reject-out-of-range precedent (guards
  reject rather than silently approximate) applies unchanged.
- **Source:** [set-cadence-day-interval-over-31-emits-monthly-only-cron](../set-cadence-day-interval-over-31-emits-monthly-only-cron/)
  "What's broken" + closure log; `crontab(5)` day-of-month field range 1–31.

## Empirical evidence

`reproduce.py` on a clean checkout (defect present):

```
interval_to_cron('31d', 13) returned '13 0 */31 * *'
  -> fires on days-of-month: [1]
FAIL: '31d' collapsed to 'monthly on the 1st' with no error — the same
      day-1-only collapse the N > 31 guard rejects.
```

## Fix

`scripts/set_cadence.py:100-105`: change the guard to `if n > 30` and reword
the message to "day interval must be <= 30 (a */N day-of-month step with
N >= 31 matches only the 1st)". Update the docstring range to 1 ≤ N ≤ 30.
Update `tests/test_set_cadence.py`: `test_day_interval_boundary_31_supported`
becomes a rejection case; add `30d` as the supported boundary. Amend the
predecessor card with a forward pointer per the "closure is not frozenness"
rule.
