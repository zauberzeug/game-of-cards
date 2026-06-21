---
title: validate-rejects-same-day-card-with-datetime-created-and-bare-date-closed-at
summary: "The cross-field `closed_at >= created` ordering check added by validate-accepts-closed-at-that-predates-created promotes a bare-date value to midnight UTC. So a card created at a sub-day datetime (e.g. `2026-06-10T20:00:00Z`) and closed with the same-day bare date (`2026-06-10`) compares as closed-before-created — closed_instant is that day's midnight, which is strictly before 20:00 — and `goc validate` reports a spurious `closed_at predates created` error. Day-granularity `closed_at` is an accepted shape, so this is a legitimately-authored card being rejected. The inverse mix (date created + datetime closed) the predecessor's comment claims to handle does sort correctly; only this direction misfires."
status: done
stage: null
contribution: medium
created: "2026-06-21T04:42:22Z"
closed_at: "2026-06-21T04:46:16Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (validate no longer flags a same-day card with datetime `created` + bare-date `closed_at`; the genuine inverted-ordering cases still fire)
  - [x] TDD: regression test in tests/test_validate_closed_at_ordering.py covers (a) datetime created + same-day bare-date closed_at -> accepted, (b) bare-date created + same-day datetime closed_at -> accepted, (c) bare-date closed_at on a strictly-earlier day than a datetime created -> rejected, (d) both-datetime intra-day inversion still rejected
  - [x] MECHANICAL: `uv run goc validate` passes on this repo's deck; plugin mirrors re-synced if engine changed
---

# `goc validate` rejects a same-day card with datetime `created` and bare-date `closed_at`

## Location

`goc/engine.py:1429-1441` — the cross-field ordering block in
`validate_card`, added by
[validate-accepts-closed-at-that-predates-created](../validate-accepts-closed-at-that-predates-created/):

```python
created_value = fm.get("created")
if created_value is not None and closed_at is not None:
    created_instant = _waiting_until_instant(created_value)
    closed_instant = _waiting_until_instant(closed_at)
    if (
        created_instant is not None
        and closed_instant is not None
        and closed_instant < created_instant
    ):
        errors.append(
            f"{t.title}: closed_at: {closed_at!r} predates created "
            f"{created_value!r} (a card cannot close before it was created)"
        )
```

The comparison runs through `_waiting_until_instant` (`goc/engine.py:877-904`),
which promotes a bare date `YYYY-MM-DD` to **midnight UTC** of that day
while honoring a datetime at full precision. The inline comment at
`engine.py:1424-1428` claims the instant comparison makes "a date-only
`created` and a same-day datetime `closed_at` sort correctly" — true in
that direction, but the opposite mix is not handled.

## What's wrong

A bare date carries only day granularity — it names a calendar day, not
an instant. Forcing it to midnight UTC and then comparing strictly
against a sub-day datetime breaks the same-day case in one direction:

| created | closed_at | created_instant | closed_instant | verdict |
|---|---|---|---|---|
| `2026-06-10` (date) | `2026-06-10T20:00:00Z` | 00:00 | 20:00 | clean (correct) |
| `2026-06-10T20:00:00Z` | `2026-06-10` (date) | 20:00 | 00:00 | **error (false positive)** |

The two rows describe the same real situation — a card created and
closed on the same calendar day — yet only one passes. The fix should
compare at **day granularity when either operand is a bare date** (the
only granularity actually known), and at full precision only when both
sides are datetimes (so the genuine intra-day inversion the predecessor
card added stays rejected).

## Empirical evidence

`reproduce.py` calls `_waiting_until_instant` and `validate_card`
directly:

```
created 2026-06-10T20:00:00Z, closed_at 2026-06-10 (same day):
  closed_instant 2026-06-10 00:00:00+00:00 < created_instant 2026-06-10 20:00:00+00:00 -> True
  validate_card errors: ['demo: closed_at: '2026-06-10' predates created '2026-06-10T20:00:00Z' (a card cannot close before it was created)']
```

With the fix applied, this same-day card validates clean while a card
whose bare-date `closed_at` is a strictly-earlier day than its datetime
`created`, and a both-datetime intra-day inversion, still produce the
error. `reproduce.py` exits 0.

## Why it matters

`goc validate` is the frontmatter-integrity gate run in pre-commit and
CI; a false positive fails the build. The engine's happy path writes
both stamps via `_utc_now_iso()` (full datetime), so it does not produce
this shape — but bare-date `closed_at` is an explicitly-accepted legacy
shape (`engine.py:1421` only requires null/ISO-date/datetime, and the
`Card.closed_at` docstring documents day granularity). Reachability is
via `goc migrate` imports of legacy day-granularity cards, hand-edited
frontmatter that closes a card with a bare date, or decomposition
rewrites that copy a datetime `created` onto a card carrying a bare-date
`closed_at`. Any such card created and closed on the same day fails
validation even though its timeline is coherent.

## Fix

In the ordering block at `engine.py:1429-1441`, when either
`created_value` or `closed_at` is a bare date (date-only granularity),
compare the two instants' `.date()` components rather than the full
instants; otherwise compare instants as today. A same-day pair then
compares equal-day (accepted), while a strictly-earlier `closed_at` day
and a both-datetime intra-day inversion both still flag.
