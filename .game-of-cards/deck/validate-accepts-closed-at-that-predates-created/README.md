---
title: validate-accepts-closed-at-that-predates-created
summary: "`goc validate` checks each timestamp's shape, calendar-validity, and closed_at/status coherence, but never compares `closed_at` against `created`. A terminal card whose `closed_at` predates its `created` (closed before it existed) passes `goc validate` with exit 0, including intra-day inversions in the datetime shape. This is the cross-field ordering axis — orthogonal to the future-date cards, which compare each field against wall-clock now."
status: active
stage: null
contribution: medium
created: "2026-06-15T05:26:59Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (validate now flags closed_at < created; defect no longer fires)
  - [ ] TDD: regression test in tests/test_validate.py covers closed_at before created (rejected), closed_at == created (accepted), closed_at after created (accepted), and an intra-day datetime inversion (rejected)
  - [ ] TDD: a card whose created or closed_at is non-ISO is unaffected by the new check (the shape error still fires, no crash on the ordering comparison)
  - [ ] MECHANICAL: `uv run goc validate` passes on this repo's deck; plugin mirrors re-synced if engine changed
worker: {who: "claude[bot]", where: main}
---

# `goc validate` accepts `closed_at` timestamps that predate `created`

## Location

- `goc/engine.py:1413-1449` — `validate_card`'s timestamp block. Each
  of `created` and `closed_at` is checked for ISO shape; `closed_at`
  is additionally checked for presence-iff-terminal-status. There is
  no comparison between the two values:

  ```python
  if "created" in fm and not _is_iso_date(fm["created"]):
      errors.append(f"{t.title}: created: {fm['created']!r} not a valid ISO ...")

  closed_at = fm.get("closed_at")
  if closed_at is not None and not _is_iso_date(closed_at):
      errors.append(f"{t.title}: closed_at: {closed_at!r} not null/ISO date/datetime")
  ...
  status_value = fm.get("status")
  if status_value in TERMINAL_STATUSES:
      if closed_at is None:
          errors.append(f"{t.title}: closed_at: must be set when status={status_value}")
  ```

## What's missing

`Card.closed_at` is documented as "the ISO timestamp the card entered
a terminal status" (`goc/engine.py:662-668`). A `closed_at` earlier
than `created` is incoherent: a card cannot enter a terminal status
before it was created. The validator catches the syntactic adjacent
failures (non-ISO shape; calendar-impossible like `2026-13-45`) and
the status-coherence failures (terminal-without-`closed_at`,
non-terminal-with-`closed_at`), but not this cross-field temporal
ordering.

This is distinct from the future-date cards
([validate-accepts-future-closed-at-timestamps](../validate-accepts-future-closed-at-timestamps/),
[validate-accepts-future-created-timestamps](../validate-accepts-future-created-timestamps/)):
those compare a single field against wall-clock *now* — an axis with a
genuine clock-skew-tolerance decision (reject / warn / tolerate). The
ordering check here compares two values *stored on the same card*
against each other. There is no external clock and no tolerance
question: creation causally precedes closure, so `closed_at >= created`
is an absolute invariant, repaired the same way the other `closed_at`
coherence violations are — a hard validation error.

## Empirical evidence

`reproduce.py` builds three `done` cards and runs `validate_card`:

```
closed_at BEFORE created (2026-01-01 < 2026-06-15): (none -> DEFECT)
closed_at 08:00 BEFORE created 12:00 same day:       (none -> DEFECT)
closed_at AFTER created (control, 2026-06-15 > 2026-01-01): (none -> correct)
```

The first two should each produce a `closed_at`-ordering error; today
the validator returns no error for either.

## Why it matters

`goc validate` is the frontmatter-integrity gate run in pre-commit and
CI. An incoherent timeline silently survives it, then feeds
`--done --since` / `--closed-since` reporting windows and any
chronological reasoning a cold reader does over the deck's history.
Engine writes always use `_utc_now_iso()` for both stamps, so the bad
shape is not produced by the happy path — reachability is via hand-edit
of frontmatter, `goc migrate` imports of legacy cards, decomposition
rewrites that copy a `created` from one card onto another, or bot
commits that bypass the pre-commit validate gate.

## Fix

In `validate_card`, after both `created` and `closed_at` pass their
shape checks and `closed_at` is non-null, parse both into UTC instants
(reuse the existing `_waiting_until_instant` ISO→instant parser, which
handles both the date-only and datetime shapes and returns `None` for
anything `_is_iso_date` rejects) and append an error when the
`closed_at` instant is strictly before the `created` instant. Guard on
both parses succeeding so a malformed value that already produced a
shape error does not crash the comparison.
