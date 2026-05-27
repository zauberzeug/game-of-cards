---
title: waiting-until-with-time-of-day-un-defers-card-at-start-of-day
summary: "The read-time guard `waiting_impedes` accepts a datetime-form `waiting_until` (`YYYY-MM-DDTHH:MM:SSZ`) but truncates it to a bare date via `_date_part` and compares `until_date > today`. A card deferred until `2026-05-27T23:59:59Z` is treated as un-impeded the entire civil day 2026-05-27, re-entering the ready/pull queue up to ~24h early. `validate_waiting_overlay`'s elapsed-wait surfacing has the same truncation. Accepted input precision (datetime) is wider than honored precision (date)."
status: open
stage: null
contribution: medium
created: "2026-05-27T03:29:18Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (a `waiting_until` of `2026-05-27T23:59:59Z`
        still impedes when evaluated during 2026-05-27).
  - [ ] TDD: `waiting_impedes` compares the full timestamp (date-only values clear
        at midnight UTC of the named day, exactly as today — no behavior change for
        bare-date `waiting_until`, future/elapsed date-only, bare-reason, no-overlay,
        or the malformed-prefix backstop the closed sibling installed).
  - [ ] TDD: `validate_waiting_overlay`'s elapsed-wait surfacing uses the same
        full-timestamp comparison (an end-of-day datetime wait is not reported as
        elapsed before it actually elapses).
  - [ ] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check`
        green) and `uv run goc validate` clean.
---

# `waiting_until` with a time-of-day un-defers the card at the start of its civil day

## Location

- `goc/engine.py:1664-1666` — `waiting_impedes` parses `waiting_until`:

  ```python
  if _is_iso_date(until):
      until_date = date.fromisoformat(_date_part(until))
  ```

  then at `goc/engine.py:1686`:

  ```python
  # Future date hides; elapsed date resurfaces the card.
  return until_date > today
  ```

- `goc/engine.py:1383-1385` — `validate_waiting_overlay` does the same
  truncation for elapsed-wait surfacing:

  ```python
  if not _is_iso_date(until):
      ...
  until_date = date.fromisoformat(_date_part(until))
  ```

- `goc/engine.py:692-697` — `_date_part` prefix-truncates any string ≥ 10
  chars to its first 10 (the date portion), discarding `THH:MM:SSZ`.

## What's broken

The datetime shape `YYYY-MM-DDTHH:MM:SSZ` is an **accepted** value for
`waiting_until`. `_is_iso_date` explicitly admits it (`goc/engine.py:662-681`,
"Accepts the legacy date-only shape AND the current datetime shape"), and the
`goc wait --until` validator advertises it verbatim in its error string
(`goc/engine.py:3922-3924`): `not a valid ISO YYYY-MM-DD or
YYYY-MM-DDTHH:MM:SSZ date`.

But the read-time guard **honors only date granularity**. `_date_part`
truncates `2026-05-27T23:59:59Z` to `2026-05-27`, and `until_date > today`
compares two civil dates. So on 2026-05-27 a card deferred to the very end of
that day evaluates `2026-05-27 > 2026-05-27` → `False` → not impeded → it
re-enters the ready/pull queue at the *start* of the 27th, up to ~24h before
its wait actually clears.

The accepted-input contract is strictly wider than the honored-input
contract: the engine takes a timestamp it then silently rounds away.

This is distinct from the three closed sibling cards:
- [read-time-date-guards-compare-utc-stamps-to-local-date](../read-time-date-guards-compare-utc-stamps-to-local-date/)
  fixed the *base* of `today` (local → UTC civil date), still date-vs-date.
- [waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date](../waiting-impedes-truncates-malformed-waiting-until-to-a-valid-prefix-date/)
  fixed *malformed* prefix garbage (`2026-05-20xx`), not valid datetimes.
- [record-card-timestamps-as-utc-datetime](../record-card-timestamps-as-utc-datetime/)
  *added* the datetime shape to `_is_iso_date` (for `created`/`closed_at`
  velocity) — which is how the datetime shape became accepted for
  `waiting_until` without any consumer honoring its time component.

## Empirical evidence

`uv run python deck/waiting-until-with-time-of-day-un-defers-card-at-start-of-day/reproduce.py`:

```
today (UTC civil)                 = 2026-05-27
waiting_until 2026-05-27T23:59:59Z -> impedes = False  (want True)
waiting_until 2026-05-27 (bare)    -> impedes = False  (want False)

At wall-clock 2026-05-27T08:00:00+00:00 the end-of-day wait has NOT elapsed,
so the card should still be impeded (hidden from the ready queue).

FAIL: end-of-day datetime wait un-defers ~16h early — time component dropped.
```

## Why it matters

The whole point of the `waiting_until` overlay is the auto-resurface read-time
guard: a deferred card stays out of the pull/ready queue until its wait
elapses. A datetime-precision deferral is the natural way to say "come back
after this afternoon's event" — but the card silently reappears at midnight,
and an autonomous `pull-card` loop will claim it before the wait is real.
Symmetrically, `validate_waiting_overlay` will *not* flag the wait as an
elapsed SLE-escalation at the right moment either, since it rounds the same
way.

## Fix

In `waiting_impedes`, compare against the wall clock at full precision instead
of truncating to a civil date. Parse `waiting_until` as a datetime (treating a
bare `YYYY-MM-DD` as midnight UTC of that day) and compare to `datetime.now(tz=utc)`
(injectable, paralleling the existing `today=` test hook — likely a `now=`
parameter). This is backward-compatible: a bare date `2026-05-27` becomes
`2026-05-27T00:00:00Z`, so it clears at the start of the 27th exactly as today.
Mirror the same change in `validate_waiting_overlay`'s elapsed-wait branch so
the read guard and the validator agree.

(An alternative framing — *reject* the datetime shape for `waiting_until` and
keep date granularity — was considered but rejected: it would break the
already-accepted input contract and the `goc wait --until` help text, and
date-precision deferral is strictly less expressive. Honoring the timestamp is
the lower-surprise, backward-compatible fix.)

**Do NOT apply the fix in this card filing.**
