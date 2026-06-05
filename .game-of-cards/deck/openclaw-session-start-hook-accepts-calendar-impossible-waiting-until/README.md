---
title: openclaw-session-start-hook-accepts-calendar-impossible-waiting-until
summary: "The OpenClaw plugin's TS port of `waiting_impedes` parses `waiting_until` with JS `Date.parse`, which rolls a calendar-impossible-but-ISO-shaped value like `2026-02-30` forward to a valid date instead of rejecting it. The Python engine rejects it (`_is_iso_date`) and keeps the card impeded; the TS port un-defers it, re-announcing a hidden card as resumable at session start. TS-port sibling of the closed engine fix."
status: done
stage: null
contribution: medium
created: "2026-06-05T05:13:19Z"
closed_at: "2026-06-05T05:16:46Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — the TS `isImpeded` agrees with the engine on a calendar-impossible `waiting_until` (`2026-02-30`) for both the bare-deferral and `waiting_on`-set cells.
  - [x] TDD: a calendar-impossible-but-ISO-shaped case (`2026-02-30`) is added to tests/test_openclaw_session_start_hook.py and asserts `isImpeded("", "2026-02-30", NOW) == true` and `isImpeded("external", "2026-02-30", NOW) == true`.
  - [x] TDD: no behavior change for genuinely valid date/datetime shapes — the existing matrix cells stay green.
  - [x] MECHANICAL: `parseWaitingUntil` in openclaw-plugin/index.ts rejects calendar-impossible dates (round-trips the parsed UTC Y-M-D against the input), mirroring the engine's `_is_iso_date` calendar check.
  - [x] PROCESS: `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# OpenClaw session-start hook accepts calendar-impossible `waiting_until`

## Location

- `openclaw-plugin/index.ts:159-173` — `parseWaitingUntil` (the TS port of
  `goc.engine._waiting_until_instant`).

## What's broken

The OpenClaw plugin ports the engine's read-time impediment guard
(`waiting_impedes`) to TypeScript so the `session_start` hook can decide which
`status: active` cards to re-announce as resumable. `parseWaitingUntil` parses
the `waiting_until` overlay with JS `Date.parse`:

```ts
function parseWaitingUntil(value: string): Date | null {
  if (ISO_DATETIME_UTC_RE.test(value)) {
    const t = Date.parse(value);
    return Number.isNaN(t) ? null : new Date(t);
  }
  if (ISO_DATE_RE.test(value)) {
    const t = Date.parse(`${value}T00:00:00Z`);
    return Number.isNaN(t) ? null : new Date(t);
  }
  return null;
}
```

`ISO_DATE_RE` / `ISO_DATETIME_UTC_RE` check *shape* only (`\d{2}` for month and
day), so a calendar-impossible-but-shaped value like `2026-02-30` or
`2026-06-31` passes the regex and reaches `Date.parse`. JS `Date.parse` is
lenient: it **rolls those forward** to a valid instant (`2026-02-30` →
`2026-03-02`, `2026-06-31` → `2026-07-01`) instead of returning `NaN`. So
`parseWaitingUntil` returns a non-null `Date`.

The Python engine rejects them. `_waiting_until_instant` gates on `_is_iso_date`
(`goc/engine.py:770-794`), which parses with the real calendar
(`date.fromisoformat` / `strptime`) and returns `False` for `2026-02-30`. So
`_waiting_until_instant` returns `None`, and `waiting_impedes` falls into its
documented `until_unparseable` backstop — "err on the side of impeding so the
card is not silently un-deferred" (`goc/engine.py:2029-2039`). The TS port's
own comment (`index.ts:182-185`) claims it implements exactly that backstop,
but `Date.parse`'s leniency defeats the claim for this whole class of inputs.

When the rolled-forward date lands in the past relative to `now`, the
divergence flips the outcome: the engine keeps the card impeded (hidden), while
the hook treats it as no-longer-deferred and announces it as a resumable active
card at session start — the precise "hidden-from-queue card still announced as
resumable" failure mode the existing engine fix
([validate-accepts-calendar-impossible-dates-that-un-defer-cards](../validate-accepts-calendar-impossible-dates-that-un-defer-cards/))
closed for the Python side.

## Empirical evidence

`reproduce.py` extracts the production `parseWaitingUntil` / `isImpeded` from
`index.ts` (the same extraction the regression test uses), runs them under
Node, and compares against the engine for the same cells (pinned
`now = 2026-05-29T12:00:00Z`, after the rolled instant of `2026-02-30`):

```
waiting_on   waiting_until  python   ts       agree
----------------------------------------------------
(none)       2026-02-30     True     False    MISMATCH
external     2026-02-30     True     False    MISMATCH
(none)       2099-01-01     True     True     OK
external     2000-01-01     False    False    OK
(none)       2026-99-99     True     True     OK

FAIL: 2 cell(s) diverge — the TS port un-defers cards the engine keeps impeded.
```

`2026-99-99` does NOT diverge because `Date.parse` returns `NaN` for it (the
regex/NaN path already yields `null`); only regex-valid, calendar-impossible
dates that roll forward slip through. The existing TS-port test only exercises
`2026-99-99`, so this class was never covered.

## Why it matters

The OpenClaw `session_start` hook reads `README.md` frontmatter directly and
runs *before* `goc validate` — it is the read-time guard for pre-validate /
hand-edited decks, exactly the surface the engine fix targeted. A human who
hand-edits a deferral to a fat-fingered `waiting_until: 2026-02-30` gets a card
the engine and the Python hook keep hidden, but the OpenClaw hook resurfaces and
announces as resumable. The reachability path is: hand-edited frontmatter →
`findActiveCards` → `isImpeded` → the session-start active-card reminder. This
is the TS-port sibling of an already-fixed engine defect; the port drifted
because `Date.parse` is not the calendar-strict parser the engine uses.

## Fix

In `parseWaitingUntil` (`openclaw-plugin/index.ts:159-173`), after `Date.parse`
succeeds, round-trip the parsed UTC `Y-M-D` against the input's date prefix and
return `null` on mismatch — rejecting the silent roll-over and matching the
engine's `_is_iso_date` calendar check. `2026-02-30` → parses to `2026-03-02` →
round-trip `"2026-03-02" !== "2026-02-30"` → `null` → `isImpeded` hits the
unparseable backstop and impedes, matching the engine.

Note: `openclaw-plugin/index.ts` is in the "NOT auto-synced" list (it is a
hand-maintained TS port, not a mirror), so it is edited directly — there is no
template to edit and no sync step.
