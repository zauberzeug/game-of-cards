---
title: waiting-until-with-time-of-day-un-defers-card-at-start-of-day
summary: "The read-time guard `waiting_impedes` accepts a datetime-form `waiting_until` (`YYYY-MM-DDTHH:MM:SSZ`) but truncates it to a bare date via `_date_part` and compares `until_date > today`. A card deferred until `2026-05-27T23:59:59Z` is treated as un-impeded the entire civil day 2026-05-27, re-entering the ready/pull queue up to ~24h early. `validate_waiting_overlay`'s elapsed-wait surfacing has the same truncation. Accepted input precision (datetime) is wider than honored precision (date)."
status: done
stage: null
contribution: medium
created: "2026-05-27T03:29:18Z"
closed_at: "2026-05-27T03:40:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (a `waiting_until` of `2026-05-27T23:59:59Z`
        still impedes when evaluated during 2026-05-27).
  - [x] TDD: `waiting_impedes` compares the full timestamp (date-only values clear
        at midnight UTC of the named day, exactly as today — no behavior change for
        bare-date `waiting_until`, future/elapsed date-only, bare-reason, no-overlay,
        or the malformed-prefix backstop the closed sibling installed).
  - [x] TDD: `validate_waiting_overlay`'s elapsed-wait surfacing uses the same
        full-timestamp comparison (an end-of-day datetime wait is not reported as
        elapsed before it actually elapses).
  - [x] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check`
        green) and `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
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

After the fix:

```
today (UTC civil)                 = 2026-05-27
waiting_until 2026-05-27T23:59:59Z -> impedes = True  (want True)
waiting_until 2026-05-27 (bare)    -> impedes = False  (want False)

validate_waiting_overlay(end-of-day) overdue = False  (want False)
validate_waiting_overlay(elapsed)    overdue = True  (want True)

PASS: end-of-day datetime wait still impedes and is not flagged overdue early.
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

## Fix (applied)

`waiting_impedes` and `validate_waiting_overlay` now compare at full timestamp
precision instead of truncating to a civil date. A new
`_waiting_until_instant` helper (`goc/engine.py`) parses `waiting_until` into a
UTC instant — a bare `YYYY-MM-DD` becomes midnight UTC of that day, a
`YYYY-MM-DDTHH:MM:SSZ` is honored at full precision — and returns `None` for
anything `_is_iso_date` rejects (the malformed backstop is preserved). A
companion `_now_instant` resolves the comparison instant: `None` → the live
clock (`datetime.now(tz=utc)`), a `datetime` → that instant, and a plain `date`
(the legacy `today=` test hook) → midnight UTC of that day. Both guards compare
`until_dt > now`, so the read guard and the validator agree on when a deferral
has elapsed.

Backward-compatible: a bare date `2026-05-27` becomes `2026-05-27T00:00:00Z`, so
it clears at the start of the 27th exactly as before, and every existing
`today=<date>` caller keeps its date-vs-date semantics.

(An alternative framing — *reject* the datetime shape for `waiting_until` and
keep date granularity — was considered but rejected: it would break the
already-accepted input contract and the `goc wait --until` help text, and
date-precision deferral is strictly less expressive. Honoring the timestamp is
the lower-surprise, backward-compatible fix.)
