---
title: sort-tiebreak-counts-closed-and-impeded-advances-edges
summary: "The queue's near-term-flow tiebreak in `sort_default` counts every `advances` edge, including `done`/`disproved`/`superseded` and `waiting_on`-impeded targets — the exact edges `compute_values` prunes from the scheduler axis at engine.py:1751. A card whose downstream is fully closed therefore out-ranks an equal-value card that unblocks no less live flow, contradicting the tiebreak's own stated rationale."
status: done
stage: null
contribution: medium
created: "2026-05-27T01:53:06Z"
closed_at: 2026-05-27T01:59:56Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero before the fix and exits 1 ("NO DEFECT: card-y ... ranks first") after — the equal-value pair breaks on `created`, not on closed-edge count.
  - [x] TDD: the tiebreak counts only `advances` targets that the value walk would traverse — i.e. target exists in `by_title`, status not in `TERMINAL_STATUSES`, and not `waiting_impedes(target)`. An impeded or terminal downstream contributes 0 to the count.
  - [x] MECHANICAL: `sort_default`'s docstring (engine.py:1872) still describes the tiebreak accurately after the change; if the count semantic is now "live direct downstream", the docstring says so.
  - [x] PROCESS: plugin mirrors re-synced (pre-commit `sync-plugin-assets`) and `goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# Queue tiebreak counts closed and impeded `advances` edges the value walk prunes

`sort_default`'s secondary sort key counts *all* `advances` edges on a
card, while the primary value axis (`compute_values`) deliberately
**prunes** terminal and impeded edges. The two halves of the same
near-term-flow concept disagree about which edges are live.

## Location

- Tiebreak: `goc/engine.py:1887`
- Value-walk prune it should mirror: `goc/engine.py:1751`

## What's broken

`sort_default` documents its key as "(-value, -direct_advances_count,
age_days)" with the tiebreak rationale "more direct downstream cards =
unblock more flow now" (engine.py:1872-1875). But the count is computed
over the raw frontmatter list:

```python
def key(t: Card):
    v, _ = values.get(t.title, (0.0, []))
    n_direct = len(t.frontmatter.get("advances") or [])   # engine.py:1887
    return (-v, -n_direct, t.created)
```

`compute_values`, walking the *same* `advances` edges for the primary
axis, skips terminal and impeded targets with an explicit rationale:

```python
dest_card = by_title[dest]
if dest_card.status in TERMINAL_STATUSES or waiting_impedes(dest_card):   # engine.py:1751
    # Scheduler axis is live-AND-workable only ...
    # a terminal descendant can no longer be unblocked, and an impeded
    # descendant ... cannot be pulled for the duration of its wait —
    # so neither may amplify a live card's priority.
    continue
```

A `done`/`disproved`/`superseded` downstream card unblocks zero flow;
an impeded one cannot be pulled. Yet each still adds 1 to `n_direct`, so
they amplify the tiebreak exactly where the value walk says they must
not. The tiebreak measures "edges I once pointed at", not "live flow I
unblock now".

This is a **derivation gap**, not a fresh design question. The tiebreak
was introduced in the design card
[rename-blocks-to-advances-and-design-value-sort](../rename-blocks-to-advances-and-design-value-sort/)
(closed 2026-05-03, README line 181) as a plain
`-len(card.frontmatter.get("advances") or [])`. The terminal/impeded
prune was added to `compute_values` (same-dated docstring) but the
tiebreak was never updated to match. The two have drifted.

## Empirical evidence

```
computed value  card-x=3.0  card-y=3.0  (equal: True)
queue order     ['card-x', 'card-y']
older card      card-y (2026-01-01) vs card-x (2026-01-02)

DEFECT CONFIRMED: card-x ranks first despite all its advances
edges being `done` (zero live flow to unblock), and despite
card-y being older. The tiebreak counted closed edges that the
value walk at engine.py:1751 prunes from the scheduler axis.
```

Two open `medium` cards with identical computed value 3.0. `card-x`
advances two `done` cards and is *newer*; `card-y` advances nothing and
is *older*. The age tiebreak (kanban WIP-aging) should put the older
`card-y` first. Instead `card-x` wins on its two closed edges — exactly
the inflation the value walk forbids. See [reproduce.py](reproduce.py).

## Why it matters

`sort_default` is the queue order every `goc` (no-arg), `goc --board`,
`next-card`, and `pull-card` reads. The tiebreak fires whenever two
cards compute to equal value — common, since contribution buckets are
coarse (high/medium/low) and many cards have no live downstream. The
result: cards with a pile of *already-closed* downstream edges silently
jump the queue ahead of equally-valuable, older, genuinely-flow-unblocking
work — and ahead of the WIP-aging discipline the final key is meant to
enforce. It is the same "closed edges must not amplify the scheduler
axis" invariant the value walk already encodes; the tiebreak just never
got the memo.

## Fix

Mirror the value-walk prune in the tiebreak. Count only `advances`
targets that exist, are non-terminal, and are not impeded:

```python
def sort_default(cards, values=None):
    if values is None:
        values = compute_values(cards)
    by_title = {c.title: c for c in cards}

    def live_direct(t: Card) -> int:
        n = 0
        for dest in t.frontmatter.get("advances") or []:
            dc = by_title.get(dest)
            if dc is None:
                continue
            if dc.status in TERMINAL_STATUSES or waiting_impedes(dc):
                continue
            n += 1
        return n

    def key(t: Card):
        v, _ = values.get(t.title, (0.0, []))
        return (-v, -live_direct(t), t.created)

    return sorted(cards, key=key)
```

Note `sort_default` is sometimes called on a filtered subset (the
docstring warns about this for `values`); `by_title` must be built from
whatever `cards` is passed, and a dangling edge (target not in the
subset) counts 0 — consistent with the value walk's dangling-edge drop
at engine.py:1739. Confirm callers either pass the full deck or accept
subset semantics for the tiebreak too.
