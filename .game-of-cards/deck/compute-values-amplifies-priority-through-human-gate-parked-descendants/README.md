---
title: compute-values-amplifies-priority-through-human-gate-parked-descendants
summary: "`compute_values` prunes only `TERMINAL_STATUSES` and `waiting_impedes` descendants from the GRPW value walk; an `open` (or `active`) descendant carrying `human_gate: decision` or `human_gate: session` is hidden from the queue (`card_is_ready` → False at `engine.py:1929`) yet still amplifies its ancestor's scheduling priority up the `advances` chain. Third axis of the same `card_is_ready` predicate the two closed siblings already covered for the terminal and impediment axes — the human-gate axis was never extended."
status: open
stage: null
contribution: medium
created: "2026-05-31T02:08:26Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decide whether a descendant hidden by `human_gate != none` should contribute to the scheduler value; record the decision + rationale in `log.md`, cross-referencing the deck-as-scheduler-vs-record contract in `AGENTS.md` and the precedents [compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/) (terminal axis) and [compute-values-amplifies-priority-through-impeded-descendants](../compute-values-amplifies-priority-through-impeded-descendants/) (impediment axis).
  - [ ] TDD: `reproduce.py` exits zero — an ancestor of a `human_gate`-parked descendant no longer inherits that descendant's value when the chosen rule is "prune"; an ancestor of a ready (`human_gate: none`) descendant still does.
  - [ ] MECHANICAL: if excluding, `value_for` and the `sort_default.live_direct` tiebreak count both skip descendants for which `dest.human_gate != "none"` (mirroring the existing `TERMINAL_STATUSES` / `waiting_impedes` prunes at `goc/engine.py:2083` and `goc/engine.py:2311`); the `compute_values` docstring states the predicate-aligned rule explicitly (every gate in `card_is_ready` participates in the prune).
  - [ ] MECHANICAL: plugin mirrors synced and `uv run goc validate` clean.
---

# `compute_values` amplifies priority through `human_gate`-parked descendants

## Location

`goc/engine.py:2083` — the descendant-prune condition inside
`value_for` (the inner recursion of `compute_values`). The matching
tiebreak counter at `goc/engine.py:2311` (`sort_default.live_direct`)
has the same shape and the same gap. The guard at
`goc/engine.py:1929` (`card_is_ready` returning False when
`human_gate != "none"`) is what hides a parked card from the pull
queue; the value walk and the tiebreak count are out of sync with
that guard's third axis.

## What's broken

`compute_values` walks the `advances` chain to compose a card's GRPW
value: `value(c) = rank(c) + γ·max(value(d) for d in advances(c))`. The
descendant-prune condition is:

```python
# engine.py:2083
if dest_card.status in TERMINAL_STATUSES or waiting_impedes(dest_card):
    # Scheduler axis is live-AND-workable only (AGENTS.md "deck
    # as scheduler vs record"): a terminal descendant can no
    # longer be unblocked, and an impeded descendant ... cannot
    # be pulled for the duration of its wait — so neither may
    # amplify a live card's priority. ...
    continue
```

The composite "ready-to-pull" predicate at `engine.py:1913-1933` has
**three** gates that hide a card from the queue:

```python
def card_is_ready(card: Card, by_title: dict[str, Card]) -> bool:
    if card.status != "open":      return False
    if card.human_gate != "none":  return False    # ← gate 2
    if waiting_impedes(card):      return False
    return True
```

The prune at `engine.py:2083` mirrors gate 1 (terminal status) and
gate 3 (impediment overlay) but **omits gate 2** (human gate). The
same gap exists in `sort_default.live_direct` at `engine.py:2311`,
which counts "workable direct descendants" for the secondary
tiebreak — both walks share the prune predicate and both leak the
`human_gate` axis.

The deck-as-scheduler-vs-record contract in `AGENTS.md` says the
scheduler axis walks `advances` edges across *live* cards; the two
prior siblings already established "live" as "live AND workable"
(`card_is_ready == True`). The `human_gate != none` axis is the only
ready-predicate gate the scheduler walk does not mirror.

## Empirical evidence

`reproduce.py` builds a minimal three-deck comparison —
`A (medium) advances B (high)` — and runs `compute_values` against
each:

```
A.value (B parked at human_gate=decision)  = 9.30   path=['B', 'self']
A.value (B impeded by waiting_on=external) = 3.00   path=['self']
A.value (B ready)                          = 9.30   path=['B', 'self']
```

A descendant parked at `human_gate: decision` behaves identically to
a ready descendant for the scheduler walk — A's value is amplified
by `0.7 × 9.0 = 6.3` even though `card_is_ready(B)` returns False and
no agent (autonomous puller, `next-card` recommendation, leverage
line) can take B until the gate is lowered. The impediment-axis
control returns the correct un-amplified value (3.0 = A's own rank)
since that fix landed in
[compute-values-amplifies-priority-through-impeded-descendants](../compute-values-amplifies-priority-through-impeded-descendants/).

## Reachability

The bug surfaces on every read path that ranks the open queue:

- `goc` / `goc --ready` — the headline list `pull-card` / autonomous
  `/loop` consult to pick the next card.
- `goc --board` — the kanban renderer that compares queue position.
- `Skill(next-card)` — the contribution-comparison recommendation.
- `render_leverage_line` (`goc/engine.py:2434`) — the
  `Pulling … (value N). Highest gated card: … (value M, …)` Andon
  advisory whose comparison uses these same values.

A deck currently carrying any chain of `A → B` where B's gate is
raised will produce inflated values for A. This repo's deck right
now has two `human_gate != none` active cards
(`support-external-game-of-cards-state-location`,
`list-game-of-cards-on-anthropic-community-marketplace`); any future
`advances` edge pointing at either would over-rank its source.

## Why it matters

The two prior siblings closed an identical-shape leak on the
*terminal* axis and the *impediment* axis. Both established the
"live-AND-workable" rule for the scheduler:

> a descendant nobody can pull … must not amplify a live card's
> priority. The scheduler walks live AND workable cards only.

A card parked at `human_gate: decision/session` matches that
description by the engine's own `card_is_ready` definition: it is
hidden from the queue exactly as a terminal or impeded card is. The
two prior fixes therefore tacitly *also* removed the assumption that
gate 2 was a separate case — by aligning the prune with the
ready-predicate everywhere, the principle generalizes naturally.

The duration argument ("human gates resolve in hours, impediments in
months, so amplification through a gate is still useful") is the
only credible counter-reading, and is the substantive question that
belongs in the DoD's PROCESS item. Either decision is recordable
without further design work; this card is the decision + the
mechanical fix that follows from it.

## Fix proposal

Two-line edit at the two leaky sites (PROCESS decision pending):

```python
# engine.py:2083  (value_for)
if (
    dest_card.status in TERMINAL_STATUSES
    or waiting_impedes(dest_card)
    or dest_card.human_gate != "none"          # ← add
):
    continue

# engine.py:2311  (sort_default.live_direct)
if (
    dc.status in TERMINAL_STATUSES
    or waiting_impedes(dc)
    or dc.human_gate != "none"                 # ← add
):
    continue
```

The natural refactor is to read both prunes from a single helper
that wraps `card_is_ready`'s negation modulo the
`status == "open"` clause (terminal status is the only progress
state that should also short-circuit; `active` descendants stay
workable for the scheduler axis). The two-line patch above is the
minimum; the helper refactor is optional and reduces future drift
when a fourth axis is added.

## Cross-references

- [compute-values-inherits-value-through-done-and-superseded-descendants](../compute-values-inherits-value-through-done-and-superseded-descendants/) (done) — terminal-axis fix.
- [compute-values-amplifies-priority-through-impeded-descendants](../compute-values-amplifies-priority-through-impeded-descendants/) (done) — impediment-axis fix.
- [parked-active-cards-are-missing-from-goc-ready-leverage-line](../parked-active-cards-are-missing-from-goc-ready-leverage-line/) (open) — related leverage-line gap; same `status == "open" ∧ human_gate != "none"` filter family but on a different reader.
