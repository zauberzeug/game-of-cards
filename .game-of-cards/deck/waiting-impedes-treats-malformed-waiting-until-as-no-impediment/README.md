---
title: waiting-impedes-treats-malformed-waiting-until-as-no-impediment
summary: "`waiting_impedes` returns `False` (card NOT hidden) the moment a present-but-unparseable `waiting_until` is encountered — BEFORE consulting the `waiting_on` reason. A card with an active reason and a garbage date therefore re-enters the pull/next queue, contradicting the docstring's promise that a reason without a usable date is an open-ended block. Bounded because `validate_card` rejects non-ISO `waiting_until`, but `waiting_impedes` runs on live (pre-validate) decks. UNVERIFIED — needs a reproduce.py."
status: done
stage: null
contribution: medium
created: "2026-05-26T20:56:27Z"
closed_at: 2026-05-26T21:13:57Z
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: reproduce.py — a card with `waiting_on` set and a malformed `waiting_until` is reported as impeded (hidden from queue), same as if the date were absent.
  - [x] TDD: fix in `goc/engine.py` `waiting_impedes` — a malformed `waiting_until` falls through to the reason check (`until_date = None`) instead of early-returning `False`.
  - [x] TDD: no behavior change for valid future/elapsed dates and for the bare-reason / bare-date paths.
  - [x] PROCESS: drop the `unverified` tag once reproduce.py lands.
worker: {who: "claude[bot]", where: main}
---

# `waiting_impedes` treats a malformed `waiting_until` as "no impediment"

## Location

`goc/engine.py:1527-1531` inside `waiting_impedes`.

## Confirmed (2026-05-26) — reproduce.py fired, then fixed

The hypothesis below held: `reproduce.py` showed the reason-plus-garbage-date
card reported `impeded=False` (defect), while every other path was already
correct. The `except` now sets `until_date = None` and falls through to the
reason check, so the same card reports `impeded=True`. The five control paths
(reason-no-date, no-overlay, bare-future, bare-elapsed, reason-plus-future)
are unchanged.

## Hypothesis (was UNVERIFIED, now confirmed)

```python
until_date: date | None = None
if until is not None:
    try:
        until_date = date.fromisoformat(_date_part(until))
    except (TypeError, ValueError):
        return False          # <-- early return, before reason is checked
if reason is None and until_date is None:
    return False
if until_date is None:
    # Reason set, no date — open-ended wait; hide from queue.
    return True
```

The docstring (`goc/engine.py:1513-1515`) says:

> A `waiting_on` reason without an elapsed `waiting_until` means the
> block is ongoing (no expected return date, or the date is in the
> future) and the card is hidden from queues.

But when `waiting_until` is present-and-unparseable, the `except`
returns `False` *before* the reason is consulted. So a card with
`waiting_on: external` plus a garbage `waiting_until` is reported as NOT
impeded — it re-enters the `pull-card` / `next-card` queue. The
correct fall-through is to treat the bad date as absent
(`until_date = None`, continue), letting the reason check at line
1534-1536 hide the card.

Severity is bounded: `validate_card` (`goc/engine.py:1090-1094`) rejects
a non-ISO `waiting_until`, so a *validated* deck cannot hold one. But
`waiting_impedes` is called on live, pre-validate decks (queue renders
run without a prior `goc validate`), so a hand-edited or mid-write card
can hit this.

## Why deferred

No reproduce.py budget this round (two confirmed defects filed). The
falsification recipe is cheap, listed below.

## Falsification recipe

Build a `Card` with `waiting_on="external"`, `waiting_until="not-a-date"`
and call `waiting_impedes(card)`. Defect fires if it returns `False`;
expected `True`. Compare against the same card with `waiting_until=None`
(returns `True` today).

Surfaced by the engine-core defect hunter during an audit-deck round.
