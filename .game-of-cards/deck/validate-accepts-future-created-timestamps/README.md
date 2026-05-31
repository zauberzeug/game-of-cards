---
title: validate-accepts-future-created-timestamps
summary: "`goc validate` rejects calendar-impossible `created` values (the `_is_iso_date` predicate runs the calendar parse) but never checks that `created <= now`. A card with `created: \"2099-12-31T00:00:00Z\"` (~73 years in the future) passes `goc validate` with exit 0, then participates in `created`-derived queries (board-age, `validate-waiting-overlay` age math, `triage` `aged_days`) with a fictional past-tense timestamp. Sibling to the open peer [validate-accepts-future-closed-at-timestamps](../validate-accepts-future-closed-at-timestamps/), which carved this case out as `out-of-scope unless the decision covers it`."
status: open
stage: null
contribution: low
created: "2026-05-31T01:05:49Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: human picks one of the fix paths in `## Decision required`; choice recorded inline (or this card resolved as a duplicate if the closed_at peer's decision rolls `created` into its own scope).
  - [ ] TDD: `reproduce.py` exits zero on the chosen behavior (rejection / warning / pass-with-skew-tolerance).
  - [ ] TDD: regression test in `tests/test_validate.py` covers `created` in the future, at-or-before now, and the chosen tolerance boundary.
  - [ ] TDD: existing `validate-accepts-future-closed-at-timestamps` reproduce + the calendar-validity regression remain green (predicate not weakened).
  - [ ] MECHANICAL: `goc validate` passes on this repo's deck; plugin mirrors re-synced if engine changed.
---

# `goc validate` accepts `created` timestamps in the future

## Location

- `goc/engine.py:1266-1267` — `validate_card`'s `created` check:

  ```python
  if "created" in fm and not _is_iso_date(fm["created"]):
      errors.append(f"{t.title}: created: {fm['created']!r} not a valid ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ date")
  ```

  Shape + calendar-validity only; no temporal-ordering check.

- `goc/engine.py:698-722` — `_is_iso_date` (the predicate behind every date
  field) parses with the real calendar but bounds nothing relative to "now".

## What's missing

The closed peer for `closed_at`
([validate-accepts-future-closed-at-timestamps](../validate-accepts-future-closed-at-timestamps/),
currently open at `human_gate: decision`) called this out explicitly:

> "Same gap applies, in principle, to `created` (future-dated cards) —
> out of scope for this card unless the decision covers it."
> "Should `created` also be bounded by `now`? (Same argument applies.)"

`created` is documented as "ISO date when the card was filed" — a
timestamp in the future contradicts that semantic. A card cannot have
been created at a time that has not yet happened. The validator catches
the adjacent failures (non-ISO shape; calendar-impossible like
`2026-13-45`, fixed by the closed peer
[validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/))
but not the temporal one.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/validate-accepts-future-created-timestamps/reproduce.py
created sample card with created=2099-12-31T00:00:00Z
goc validate exit code: 0
DEFECT: validator accepts created ~73 years in the future
```

## Why it matters

**Reachability path.** Engine writes use `_utc_now_iso()` for `created`
(`_cmd_new` at `engine.py:4409`), so the offending input is **not**
produced by shipping code in normal operation. Realistic input paths
match the closed_at peer's analysis:

1. **Hand-edit.** Decomposition flows, `goc move` round-trips, manual
   frontmatter edits during card refactoring.
2. **Clock skew on a runner.** A CI worker or container with a wildly
   wrong system clock writes a future timestamp without any guard.
3. **Migration tooling.** A bulk-import script (e.g., from external
   tracker) that miscomputes ISO timestamps.

Downstream `created`-consuming surfaces that quietly drift on a future
value:

- `_cmd_triage` at `engine.py:4911-4915` computes `aged_days = today -
  date.fromisoformat(_date_part(t.created))` — a future `created`
  produces a **negative** aged_days. `goc triage` then sorts parked
  cards with that negative number leading the queue ("oldest first").
- `validate_waiting_overlay` and similar age-based advisories.
- `--since YYYY-MM-DD` queries that compare `created` lexicographically.

The blast radius is small (sort drift, phantom-young cards in age
queries), but the cost of the check is one date comparison per card per
`goc validate` run — identical shape to the fix already under
deliberation for `closed_at`.

## Decision required

This card's decision **collapses to the same three-way choice** that
the closed_at peer is parked on:

1. **Hard reject with no tolerance.** Add `if created_instant > now:
   errors.append(...)` in `validate_card`. Risk: a CI runner ~1 minute
   ahead of UTC trips on a card it just created.
2. **Hard reject with a small skew tolerance.** Same as (1) but allow
   `now + N` for `N ∈ {60s, 5min, 1h}` to swallow NTP drift.
3. **Warning, not error.** Surface a `WARN` line, keep exit 0. Aligns
   with `STALE_BLOCKED`-style advisories.

**Likely resolution:** when the closed_at peer is decided, this card
either (a) gets the same answer applied to `created` and is closed in
the same fix, or (b) is explicitly disproved as out-of-scope and stays
unfixed. The choice belongs to the human reviewing the closed_at peer
— this card exists so the answer is recorded against a concrete
sibling rather than left as the `companion check for created and
waiting_until either confirmed in scope or explicitly out of scope`
TODO in the closed_at peer's DoD.

## Fix sketch (depending on decision)

Reuse the `_is_in_future` helper sketched in the closed_at peer:

```python
def _is_in_future(value, *, tolerance: timedelta = timedelta(0)) -> bool:
    instant = _closed_at_instant(value)  # parses date OR datetime
    if instant is None:
        return False
    return instant > datetime.now(timezone.utc) + tolerance
```

Then in `validate_card` after the `_is_iso_date` check on `created`:

```python
if "created" in fm and _is_iso_date(fm["created"]):
    if _is_in_future(fm["created"], tolerance=_CREATED_SKEW):
        errors.append(
            f"{t.title}: created: {fm['created']!r} is in the future "
            f"(UTC now {_utc_now_iso()}); created timestamps must be at-or-before now"
        )
```

`_CREATED_SKEW` is the policy constant set by the decision (0 / 60s /
5min / 1h), shared with `_CLOSED_AT_SKEW` if both fields fall under the
same fix.

## Dedup proof

- Closed peer: [validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/)
  tightens `_is_iso_date` for **calendar-impossible** dates
  (`2026-13-45`). It does **not** add a temporal-ordering check;
  `2099-12-31` is calendar-valid and survives. Different invariant.
- Open peer: [validate-accepts-future-closed-at-timestamps](../validate-accepts-future-closed-at-timestamps/)
  covers `closed_at` future-dated, parked at `human_gate: decision`.
  That card explicitly carves `created` out as out-of-scope unless the
  decision covers it — this card is the carve-out's filing.
- Sibling family: [waiting-until-with-impossible-time-passes-validate-then-crashes-reads](../waiting-until-with-impossible-time-passes-validate-then-crashes-reads/)
  (DONE) and [validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/)
  (DONE) cover `waiting_until` shape/parse failures. This card covers
  **`created` temporal-ordering**. No overlap.
- Grep against `goc --status open` / `--status disproved` / closed deck:
  no card asks "should validate enforce `created <= now`?". Distinct.
