---
title: validate-accepts-future-closed-at-timestamps
summary: "`goc validate` rejects calendar-impossible `closed_at` values (the closed peer [validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/) tightened `_is_iso_date`) but never checks that `closed_at <= now`. A card with `closed_at: \"2099-12-31T00:00:00Z\"` (~73 years in the future) passes `goc validate` with exit 0, then participates in `--done --since` / `--closed-since` windows with a fictional past-tense timestamp. Engine writes always use `_utc_now_iso()`, so reachability is via hand-edit, decomposition rewrites, or CI clock skew."
status: open
stage: null
contribution: low
created: "2026-05-30T10:13:11Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: human picks one of the fix paths in `## Decision required`; the choice is recorded inline.
  - [ ] TDD: `reproduce.py` exits zero on the chosen behavior (rejection / warning / pass-with-skew-tolerance).
  - [ ] TDD: regression test in `tests/test_validate.py` covers `closed_at` in the future, at-or-before now, and the chosen tolerance boundary; companion check for `created` and `waiting_until` either confirmed in scope or explicitly out of scope and noted in log.md.
  - [ ] TDD: existing `validate-accepts-calendar-impossible-dates-that-un-defer-cards` regression test still passes (shape/calendar check not weakened).
  - [ ] MECHANICAL: `goc validate` passes on this repo's deck; plugin mirrors re-synced if engine changed.
---

# `goc validate` accepts `closed_at` timestamps in the future

## Location

- `goc/engine.py:1195-1197` — `validate_card`'s `closed_at` check:

  ```python
  closed_at = fm.get("closed_at")
  if closed_at is not None and not _is_iso_date(closed_at):
      errors.append(f"{t.title}: closed_at: {closed_at!r} not null/ISO date/datetime")
  ```

- `goc/engine.py:1212-1222` — only checks that `closed_at` is **set** for
  terminal statuses and **null** for non-terminal. No bound on the value's
  relationship to "now":

  ```python
  status_value = fm.get("status")
  if status_value in TERMINAL_STATUSES:
      if closed_at is None:
          errors.append(f"{t.title}: closed_at: must be set when status={status_value}")
      ...
  elif closed_at is not None:
      errors.append(
          f"{t.title}: closed_at: must be null when status is non-terminal"
          ...
      )
  ```

- `goc/engine.py:687` — `_is_iso_date` (the predicate behind every date
  field) is shape + calendar-validity only; no temporal-ordering.

## What's missing

`closed_at` is documented as "a single date per terminal exit" (see
`Card.closed_at` at `goc/engine.py:532-537`). A timestamp in the future
contradicts the field's semantic: a card cannot have been closed at a
time that has not yet happened. The validator catches the syntactic
adjacent failures (non-ISO shape; calendar-impossible like `2026-13-45`)
but not the temporal one. Same gap applies, in principle, to `created`
(future-dated cards) — out of scope for this card unless the decision
covers it.

The validator's contract is now strictly weaker than the implicit
invariant `closed_at <= now` that consumers assume:

- `--done --since YYYY-MM-DD` (engine.py:1964) silently includes a card
  whose `closed_at` is `2099-12-31` for any `--since` in this century.
- `--closed-since WINDOW` (engine.py:2027) compares against `now -
  window`; a future timestamp passes the `>= threshold` test trivially
  for any reasonable window, so audit windows include fictional closures.
- `goc validate`'s own date-field tightening peer
  ([validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/),
  closed 2026-05-27) set the precedent that "validate's date predicate
  should be no weaker than consumer parsers."

## Empirical evidence

```
$ uv run python .game-of-cards/deck/validate-accepts-future-closed-at-timestamps/reproduce.py
created sample card with closed_at=2099-12-31T00:00:00Z
goc validate exit code: 0
goc validate output (tail):
OK  sample-future-closed
DEFECT: validator accepts closed_at ~73 years in the future
```

## Why it matters

**Reachability path.** The engine itself always writes `closed_at` via
`_utc_now_iso()` (`_cmd_done` at engine.py:3263; `_cmd_status` for
`disproved`/`superseded` at engine.py:3349; `_auto_populate_worker`-adjacent
flips at engine.py:4009). So the offending input is **not** produced by
shipping code in normal operation. The realistic input paths are:

1. **Hand-edit.** Agents and humans hand-edit frontmatter when migrating,
   decomposing, or repairing cards — `goc move` and decomposition flows
   routinely round-trip frontmatter through human / model edits.
2. **Clock skew on a runner.** A CI worker or container with a wildly
   wrong system clock writes a future timestamp without any guard.
3. **Manual closure backdating that overshoots.** A user typing
   `2026-13-01` (intending `2027-01-01`) is caught today; one typing
   `2030-01-01` is not.

The blast radius is small (audit windows show a phantom closure; deck
read-paths don't crash), but the cost of the check is one date
comparison per terminal card per `goc validate` run.

## Decision required

Three credible fix paths; the human must pick one (or compose):

1. **Hard reject with no tolerance.** Add `if closed_at_instant > now:
   errors.append(...)` in `validate_card`. Simplest. Risk: a CI runner
   ~1 minute ahead of UTC could trip on a card it just closed.
2. **Hard reject with a small skew tolerance.** Same as (1) but allow
   `now + N` for `N ∈ {60s, 5min, 1h}`. Picks a constant that swallows
   normal NTP drift without missing a 100-year typo. The closed peer
   `validate-accepts-calendar-impossible-dates-that-un-defer-cards`
   chose hard-rejection with no tolerance for shape — consistent
   policy is hard-reject here too.
3. **Warning, not error.** Surface a `WARN` line but keep exit 0.
   Aligns with `STALE_BLOCKED`-style advisories. Risk: warn-only
   defects get ignored.

Out-of-scope on this card unless the decision says otherwise:

- Should `created` also be bounded by `now`? (Same argument applies.)
- Should `closed_at >= created` be enforced? (A separate temporal
  invariant — flag a sibling card if confirmed.)

## Fix sketch (depending on decision)

Add a helper next to `_closed_at_instant` (engine.py:2062):

```python
def _is_in_future(value, *, tolerance: timedelta = timedelta(0)) -> bool:
    instant = _closed_at_instant(value)
    if instant is None:
        return False
    return instant > datetime.now(timezone.utc) + tolerance
```

Then in `validate_card` after the `_is_iso_date` check:

```python
if closed_at is not None and _is_iso_date(closed_at):
    if _is_in_future(closed_at, tolerance=_CLOSED_AT_SKEW):
        errors.append(
            f"{t.title}: closed_at: {closed_at!r} is in the future "
            f"(UTC now {_utc_now_iso()}); closure timestamps must be at-or-before now"
        )
```

`_CLOSED_AT_SKEW` is the policy constant set by the decision (0 / 60s
/ 5min / 1h).

## Dedup proof

- Closed peer: [validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/)
  tightens `_is_iso_date` for **calendar-impossible** dates
  (`2026-13-45`). It does **not** add a temporal-ordering check; `2099-12-31`
  is calendar-valid and survives. Different invariant, different defect.
- Sibling family: [waiting-until-with-impossible-time-passes-validate-then-crashes-reads](../waiting-until-with-impossible-time-passes-validate-then-crashes-reads/)
  and [validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/)
  cover `waiting_until` shape/parse failures. This card covers
  **`closed_at` temporal-ordering**. No overlap.
- Grep against `goc --status open` / `--status disproved` / closed deck:
  no card asks "should validate enforce `closed_at <= now`?". Distinct.
