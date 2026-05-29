---
title: compute-values-amplifies-priority-through-impeded-descendants
summary: "`compute_values` prunes only TERMINAL descendants from the GRPW value walk; an `open` descendant carrying an active `waiting_on` impediment overlay is hidden from the queue (`card_is_ready` → False) yet still amplifies its ancestor's scheduling priority up the `advances` chain. A descendant nobody can work for months inflates a live card's rank — the exact distortion the terminal-pruning fix removed, left unpatched for the impediment axis the blocked-status redesign introduced."
status: done
stage: null
contribution: medium
created: "2026-05-26T23:42:05Z"
closed_at: "2026-05-26T23:46:04Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] PROCESS: decide whether a descendant hidden by an active impediment overlay should contribute to the scheduler value; record the decision + rationale in log.md, cross-referencing the deck-as-scheduler-vs-record contract in AGENTS.md and the precedent [compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/).
  - [x] TDD: reproduce.py exits zero — an ancestor of a far-future-impeded descendant no longer inherits that descendant's value; an ancestor of a workable (non-impeded, open) descendant still does.
  - [x] MECHANICAL: if excluding, `value_for` skips descendants for which `waiting_impedes(dest)` is True (mirroring the existing `TERMINAL_STATUSES` prune at `engine.py:1740`); the `compute_values` docstring states the impediment-aware rule explicitly.
  - [x] MECHANICAL: plugin mirrors synced and `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# `compute_values` amplifies priority through impeded (`waiting_on`) descendants

## Location

`goc/engine.py:1740-1745` — the descendant-prune condition inside
`value_for` (the inner recursion of `compute_values`). The guard at
`engine.py:1617` (`card_is_ready` → `waiting_impedes`) is what hides an
impeded card from the pull queue; the two are out of sync.

## What's broken

`compute_values` walks the `advances` chain to compose a card's GRPW
value: `value(c) = rank(c) + γ·max(value(d) for d in advances(c))`. It
prunes descendants only when their status is **terminal**:

```python
if by_title[dest].status in TERMINAL_STATUSES:
    # Scheduler axis is live-only (AGENTS.md "deck as scheduler
    # vs record"): a terminal descendant can no longer be
    # unblocked, so it must not amplify a live card's priority.
    # Such edges live on the record axis, walked elsewhere.
    continue
```

But the blocked-status redesign introduced a *second* way for a
descendant to be un-workable: an `open` card carrying an active
impediment overlay (`waiting_on` reason, or a future `waiting_until`).
Such a card is deliberately hidden from the queue — `card_is_ready`
returns False via `waiting_impedes` (`engine.py:1617`):

```python
def card_is_ready(card: Card, by_title: dict[str, Card]) -> bool:
    if card.status != "open":      return False
    if card.human_gate != "none":  return False
    if waiting_impedes(card):      return False
    return True
```

The value walk does **not** consult `waiting_impedes`. So a descendant
that no one can pull — possibly for months, until its `waiting_until`
elapses or its `waiting_on` is cleared — still contributes its full
discounted rank up the chain. The scheduler comment claims the axis is
"live-only", but an impeded-and-hidden card is, for scheduling purposes,
exactly as un-workable as a terminal one for the duration of its wait.

This is the impediment-axis analogue of the already-fixed
[compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/)
(done): that card removed value amplification through *terminal*
descendants. The fix never extended to the `waiting_on` overlay, which
was introduced by a sibling card
([add-waiting-overlay-with-reason-and-until-date](../add-waiting-overlay-with-reason-and-until-date/))
that never touched `compute_values`.

## Empirical evidence

`reproduce.py` builds a minimal deck `A (low) advances B (high)` and
compares `B` impeded (open, `waiting_on: external`,
`waiting_until: 2027-01-01`) against `B` terminal (`done`):

```
B impeded (waiting_until 2027): A.value = 7.3 | B hidden from queue: True
B terminal (done):              A.value = 1.0
```

`A` is a `low` card (rank 1.0). When `B` is `done`, `A.value` correctly
collapses to its own rank (1.0) — the terminal prune fired. When `B` is
merely impeded-and-hidden, `A.value` is **7.3** (`1.0 + 0.7·9.0`): the
hidden descendant amplifies `A`'s scheduling priority 7.3×, even though
`B` is invisible to the picker for ~7 months.

## Why it matters

The picker sorts the `--ready` queue by `value` (GRPW). A live,
genuinely-workable card can be ranked above another live card purely
because it has an impeded descendant nobody can act on. The deck's
stated contract is that the scheduler axis walks `advances` across
*live, workable* cards (AGENTS.md, "deck as scheduler vs deck as
record"); an impeded-and-hidden descendant violates that the same way a
terminal one did. The distortion is self-inflicted by the very overlay
mechanism meant to *hide* un-workable cards — it hides them from the
queue but not from the value math.

## Fix

Mirror the existing terminal-status prune. In `value_for`, after the
dangling-edge check, skip any descendant for which the impediment guard
fires:

```python
dest_card = by_title[dest]
if dest_card.status in TERMINAL_STATUSES or waiting_impedes(dest_card):
    continue
```

This is **self-clearing** by construction, exactly like `waiting_impedes`
itself: `compute_values` is recomputed on every invocation, so when a
`waiting_until` elapses or a `waiting_on` is cleared, the descendant
re-enters the value walk with no manual action — the same read-time-guard
discipline the overlay already uses for queue visibility.

The PROCESS DoD item exists because the precedent card recorded an
explicit decision (exclude terminal descendants from the scheduler
axis); this card should record the parallel decision for the impediment
axis rather than assume it. The recommendation is to exclude, matching
the precedent and the "live-only scheduler" contract — but a decision
that *deferred* (a `waiting_on: deferred` postponement) descendant
should perhaps still bias priority is worth one line of consideration
before implementing.
