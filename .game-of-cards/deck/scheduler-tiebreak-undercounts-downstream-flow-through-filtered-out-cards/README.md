---
title: scheduler-tiebreak-undercounts-downstream-flow-through-filtered-out-cards
status: done
stage: null
contribution: medium
created: "2026-06-07T05:28:15Z"
closed_at: "2026-06-07T05:33:57Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: |
  sort_default's near-term-flow tiebreak builds its by_title lookup from the
  (filtered) card list it is handed, so a live downstream card hidden by the
  display filter counts as zero unblocked flow — inverting the order of
  equal-value cards on the board, the open queue, and the leverage line. The
  value axis already runs on the full deck; the tiebreak should too.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the tiebreak ranks the higher-live-flow card first)
  - [x] TDD: a regression test asserts sort_default orders equal-value cards by full-deck live_direct even when the downstream targets are absent from the sorted subset
  - [x] MECHANICAL: sort_default accepts the full-deck by_title; render_board, the leverage line, render_active_notice, and _cmd_default thread it (they already hold full_by_title)
  - [x] MECHANICAL: the sort_default docstring no longer equates a filtered-out-but-live target with a dangling edge
worker: {who: "claude[bot]", where: main}
---

# scheduler-tiebreak-undercounts-downstream-flow-through-filtered-out-cards

## Location

`goc/engine.py:2356` — `sort_default`, specifically `by_title` at line 2381
and `live_direct` at 2383–2395. Call sites that hand it a filtered subset
while holding the full deck: `render_board` (`engine.py:2661`), the leverage
line (`engine.py:2760`), `render_active_notice` (`engine.py:2780`), and
`_cmd_default` (`engine.py:3173`).

## What's broken

The GRPW sort's key is `(-value, -live_direct(t), created)`. The `value` is
computed on the **full deck** and threaded in (`_cmd_default` builds
`full_values = compute_values(cards)` at `engine.py:3172` and passes it). But
the near-term-flow tiebreak builds its own lookup from whatever list it was
handed:

```python
2381    by_title = {c.title: c for c in cards}

2383    def live_direct(t: Card) -> int:
            ...
2389            dc = by_title.get(dest)
2390            if dc is None:
2391                continue
2392            if not card_is_workable_for_scheduler(dc):
2393                continue
2394            n += 1
```

At every real call site that list is a **status-filtered subset**, not the
full deck. `render_board` sorts each status column on its own
(`sort_default(by_status[c], ...)`), `_cmd_default` sorts the post-filter
`filtered` list, the leverage line sorts only `open_gated`, and
`render_active_notice` sorts only the `active` cards. So an `open` card whose
`advances` target is `active` (the normal case while that downstream is being
worked) finds `by_title.get(dest) is None` and scores 0 live downstream —
identical to a card that unblocks nothing.

The docstring (`engine.py:2374–2377`) acknowledges the subset scoping but
defends it by equating a filtered-out target with a dangling edge:

> The live-edge tiebreak builds `by_title` from whatever `cards` is passed;
> a dangling edge (target not in the subset) counts 0, consistent with the
> value walk's dangling-edge drop at engine.py:1739.

That analogy is wrong. `compute_values` always runs on the full deck, so the
value walk never drops a *live* edge — only genuinely dangling ones (target
absent from the whole deck). The tiebreak, run on a subset, drops live edges
the display filter merely hid. The two axes therefore disagree: value counts
the full graph, the tiebreak counts only the visible slice. Every other
renderer in this file (`render_board`, `render_json`, `render_table`) already
takes a `by_title` parameter threaded with the full deck for exactly this kind
of consistency — `sort_default` is the lone holdout, which is the tell that
this is an oversight, not a deliberate design.

## Empirical evidence

`reproduce.py` builds four cards: `a-open-two-live` (open, medium) advances
both `h-active-high` (active) and `l-active-low` (active);
`x-open-one-live` (open, medium, **older** created) advances only
`h-active-high`. On the full deck the two open cards tie at value 9.3. A
unblocks two live downstream cards, X unblocks one, so the tiebreak's own
rationale says A first. Filtering to the open queue and sorting with full-deck
values (post-fix output):

```
values: {'h-active-high': 9.0, 'l-active-low': 1.0, 'a-open-two-live': 9.3, 'x-open-one-live': 9.3}
live_direct full deck -> A: 2 X: 1
subset-scoped order (no by_title): ['x-open-one-live', 'a-open-two-live']
full-deck order: ['a-open-two-live', 'x-open-one-live']
PASS: higher-live-flow card (A) ranked first
```

The `subset-scoped order` line is the bug: both `live_direct` values collapse
to 0 in the subset (H and L are filtered out), so the tie falls through to
`created` and the **older** X wins. The `full-deck order` line is the fix:
threading the full-deck `by_title` lets the tiebreak see A's two live
downstream cards vs X's one, ranking A first.

## Why it matters

This is a correctness bug in the deck's core scheduler ordering, reachable
through everyday reads: `goc --status open`, `goc --ready`, the board's per-
column sort, and the `pull-card` leverage line all funnel through
`sort_default` with a filtered subset. Whenever a high-leverage open card's
downstream is `active` (i.e. someone is already working the thing it unblocks),
its near-term-flow score silently drops to zero and it can be out-ranked by an
equal-value card that unblocks strictly less live work. The queue mis-prioritises
quietly — no crash, just the wrong card at the top.

## Fix

Give `sort_default` an optional `by_title` parameter (mirroring `render_board`
/ `render_json` / `render_table`), and have `live_direct` use it when present:

```python
def sort_default(cards, values=None, by_title=None):
    if values is None:
        values = compute_values(cards)
    if by_title is None:
        by_title = {c.title: c for c in cards}
    ...
```

Thread `full_by_title` from the call sites that already hold it: `_cmd_default`
(`by_title=full_by_title`), `render_board` (it builds `by_title` at line 2655),
the leverage line and `render_active_notice` (build/accept the full-deck
lookup). Update the docstring to stop equating a filtered-out-but-live target
with a dangling edge. A genuinely dangling edge (target absent from the full
deck) still counts 0 because `card_is_workable_for_scheduler` never sees it.
