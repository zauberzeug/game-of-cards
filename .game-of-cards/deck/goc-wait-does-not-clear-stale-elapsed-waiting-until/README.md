---
title: goc-wait-does-not-clear-stale-elapsed-waiting-until
summary: "UNVERIFIED. `goc wait <title> --reason external` (no `--until`) only writes `waiting_on` and leaves any pre-existing `waiting_until` in place. If that stored date is already elapsed, `waiting_impedes` returns False (an elapsed `waiting_until` always resurfaces the card, even with a reason set), so the freshly-set open-ended external wait is silently ignored and the card stays pullable. Needs confirmation that this is unintended vs. the documented elapsed-resurfaces semantics."
status: open
stage: null
contribution: low
created: "2026-05-27T07:40:12Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] PROCESS: decide whether re-setting a `waiting_on` reason via `goc wait` should refresh/clear a stale elapsed `waiting_until` (or warn); record the decision in log.md.
  - [ ] TDD: if the behavior is a bug, a reproduce.py demonstrates that `goc wait <card> --reason external` on a card with an elapsed `waiting_until` leaves `card_is_ready == True`, and the fix makes it False (or warns); promote off `unverified` when it lands.
---

# `goc wait --reason` does not clear a stale elapsed `waiting_until`

**UNVERIFIED** — code-read confirmed, behavioral repro and intent-call deferred.

## Hypothesis (file:line)

`goc/engine.py:3996-3999` (the `goc wait` overlay setter):

```python
if new_reason is not None:
    fm["waiting_on"] = new_reason
if new_until is not None:
    fm["waiting_until"] = new_until
```

`goc wait <title> --reason external` with no `--until` leaves `new_until`
None, so a pre-existing `waiting_until` is untouched. If that stored date
is already in the past, `waiting_impedes` (`goc/engine.py:1744-1745`)
returns False:

```python
# Future instant hides; elapsed instant resurfaces the card.
return until_dt > now
```

An elapsed `waiting_until` resurfaces the card *even though a `waiting_on`
reason is now set* — so the user's freshly-declared open-ended external
wait is silently a no-op and the card stays in the pull queue.

## Why deferred

The documented model (`waiting_impedes` docstring) says an elapsed
`waiting_until` deliberately resurfaces the card as an SLE-escalation
signal. So this may be working-as-intended: the operator is expected to
clear the stale date. The open question is whether `goc wait` setting a
*new reason* should refresh/clear the old date or at least warn — a small
UX/semantics call, not a clear-cut bug. Hence `unverified` + a PROCESS
DoD item to settle intent first.

## Falsification recipe

1. Create a card with `waiting_until: 2020-01-01` (elapsed) and no `waiting_on`.
2. Run `uv run goc wait <card> --reason external`.
3. Assert `card_is_ready(card, by_title)` — expected (if bug) False, actual True.

## Surfaced by

audit-deck static hunt (general-purpose agent, engine.py core-logic seam), 2026-05-27.
