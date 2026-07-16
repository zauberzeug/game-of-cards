---
title: set-cadence-help-epilog-advertises-31d-that-the-guard-rejects
summary: "The argparse epilog of scripts/set_cadence.py still advertises `<N>d (<=31)` although the day-interval guard was tightened to reject anything above 30 (a `*/31` day-of-month step matches only the 1st and fires monthly). A user following `--help` and running `--pull 31d` gets exit 2. One-token fix: `(<=31)` → `(<=30)`."
status: active
stage: null
contribution: low
created: "2026-07-16T01:02:08Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (the epilog's advertised day cap is accepted by interval_to_cron)
  - [ ] MECHANICAL: scripts/set_cadence.py epilog reads `<N>d (<=30)`
worker: {who: "claude[bot]", where: main}
---

# set_cadence --help epilog advertises 31d that the guard rejects

## Location

`scripts/set_cadence.py:219` (argparse epilog) vs the guard at
`scripts/set_cadence.py:101-106`.

## What's broken

The help text promises:

```python
epilog="Interval specs: <N>h (1,2,3,4,6,8,12), 24h, <N>d (<=31), or 1w. Commit & push to apply.",
```

but the guard rejects the advertised maximum:

```python
if n > 30:
    raise ValueError(
        f"{spec!r}: day interval must be <= 30 "
        "(cron's day-of-month field caps at 31, so a */N step with "
        "N >= 31 matches only the 1st and fires monthly)"
    )
```

The closed card
[set-cadence-accepts-31d-which-collapses-to-monthly-only-cron](../set-cadence-accepts-31d-which-collapses-to-monthly-only-cron/)
tightened the cap from 31 to 30 but left the epilog's `(<=31)`
remnant behind.

## Empirical evidence

`reproduce.py` output on the defective code:

```
epilog advertises day cap: 31
interval_to_cron('31d') -> ValueError: '31d': day interval must be <= 30 ...
DEFECT: --help advertises a day interval the guard rejects
```

## Why it matters

Reachability: `Skill(tune-cadence)` wraps this script; an agent or
human reading `--help` to pick a valid spec gets exit 2 on the
documented boundary value.

## Fix

`scripts/set_cadence.py:219`: change `(<=31)` to `(<=30)`.
