---
title: goc-wait-does-not-clear-stale-elapsed-waiting-until
summary: "UNVERIFIED. `goc wait <title> --reason external` (no `--until`) only writes `waiting_on` and leaves any pre-existing `waiting_until` in place. If that stored date is already elapsed, `waiting_impedes` returns False (an elapsed `waiting_until` always resurfaces the card, even with a reason set), so the freshly-set open-ended external wait is silently ignored and the card stays pullable. Needs confirmation that this is unintended vs. the documented elapsed-resurfaces semantics."
status: open
stage: null
contribution: low
created: "2026-05-27T07:40:12Z"
closed_at: null
human_gate: decision
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

## Decision required

The behavioral repro is now **confirmed** (2026-05-27, pull-card session).
Driving `waiting_impedes` directly:

| stored overlay | `impedes` |
|---|---|
| `waiting_on: external` + `waiting_until: 2020-01-01` (elapsed) | **False** (card stays pullable) |
| `waiting_on: external`, no `waiting_until` | True (hidden, as intended) |
| no `waiting_on`, `waiting_until: 2020-01-01` (elapsed) | False (SLE resurfacing) |

So `goc wait <card> --reason external` on a card that already carries an
elapsed `waiting_until` silently no-ops: the elapsed date wins over the
fresh reason and the card never leaves the queue. That much is fact.

What is **not** decided is the intent — whether this is a bug or the
documented elapsed-resurfaces semantics doing its job. The resolution is
an API-contract / UX taste call on `goc`'s own surface, with no project
consultation rubric to settle it. Three defensible options:

- **A — auto-clear the stale date.** When `goc wait` sets a `waiting_on`
  reason and no `--until` is passed, drop any pre-existing *elapsed*
  `waiting_until` so the open-ended wait takes effect. Idempotent, matches
  naive intent. Cost: silently mutates stored state the operator did not
  name (tension with the model's explicit-over-implicit, read-time-guard
  ethos).
- **B — warn, do not mutate.** `goc wait --reason X` detects a stale
  elapsed `waiting_until` and prints a warning (`stale waiting_until
  2020-01-01 leaves this card pullable; pass --until or clear it`), leaving
  state untouched. Respects explicit-over-implicit; no surprise mutation.
  Cost: the wait still no-ops until the operator acts.
- **C — working-as-intended.** The elapsed date is deliberately an
  SLE-escalation signal that overrides any reason; the operator is expected
  to clear it. Close this card as `disproved` (not a bug); the documented
  footgun stands.

Recommendation: **B** — it surfaces the silent no-op (the actual harm)
without `goc wait` reaching into a field the caller did not pass, which
fits the overlay's read-time-guard / no-implicit-mutation design. But this
is the maintainer's contract call to make; resolve via `goc decide` to
lower the gate and pick the path, then the fix (or `disproved` close) can
proceed.

## Surfaced by

audit-deck static hunt (general-purpose agent, engine.py core-logic seam), 2026-05-27.
