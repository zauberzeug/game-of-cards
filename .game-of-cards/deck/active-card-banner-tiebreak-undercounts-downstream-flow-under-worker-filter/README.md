---
title: active-card-banner-tiebreak-undercounts-downstream-flow-under-worker-filter
status: done
stage: null
contribution: low
created: "2026-06-27T01:36:40Z"
closed_at: "2026-06-27T01:39:31Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the active-card banner ranks the higher-live-flow card first under a --worker filter)
  - [x] TDD: a regression test asserts render_active_notice orders equal-value active cards by full-deck live_direct even when the downstream targets are absent from the worker-scoped subset
  - [x] MECHANICAL: render_active_notice accepts a full-deck by_title and threads it into sort_default (mirroring render_leverage_line / render_table / render_board); _cmd_default passes full_by_title
worker: {who: "claude[bot]", where: main}
---

# active-card-banner-tiebreak-undercounts-downstream-flow-under-worker-filter

## Location

`goc/engine.py` — `render_active_notice` (around line 3147) and its sole
call site in `_cmd_default` (around line 3601).

## What's broken

`render_active_notice` sorts the active-card banner with `sort_default`,
but — unlike every sibling renderer (`render_table`, `render_board`,
`render_json`, `render_leverage_line`) — it does **not** accept a
`by_title` parameter. It builds the tiebreak lookup internally from
whatever `cards` list it is handed:

```python
def render_active_notice(cards, *, values=None):
    if values is None:
        values = compute_values(cards)
    active = sort_default(
        [t for t in cards if t.status == "active"],
        values=values,
        by_title={t.title: t for t in cards},   # <-- built from the passed-in subset
    )
```

`sort_default`'s near-term-flow tiebreak (`-value, -live_direct, created`)
counts only downstream `advances` targets present in `by_title`. When
`by_title` is a subset, live downstream cards outside that subset score
zero, so equal-value active cards fall through to the `created`
tiebreak and sort oldest-first instead of highest-live-flow-first.

For most of this function's life that was harmless: `_cmd_default`
passed the **full deck** as `cards`, so the internal `by_title` was
complete. But `active-card-banner-ignores-worker-filter` (closed
2026-06-24) changed the call site to pass a **worker-scoped subset**
under `--worker`:

```python
notice_cards = (
    [t for t in cards
     if args.worker.lower() in _worker_who(t.frontmatter.get("worker")).lower()]
    if args.worker else cards
)
active_notice = render_active_notice(notice_cards, values=full_values) ...
```

That re-introduced — on this one path — exactly the subset-scoping
tiebreak bug that `scheduler-tiebreak-undercounts-downstream-flow-through-filtered-out-cards`
(closed 2026-06-07) set out to eliminate everywhere. That card's DoD
even asserted "render_active_notice threads [full by_title]", but the
function never took a `by_title` parameter — the fix relied on the call
site passing the full deck, an invariant the later worker-filter change
silently broke.

Under `goc --worker <name>`, a downstream card owned by a *different*
worker (the normal case while someone else works the thing this card
unblocks) is absent from the worker-scoped `by_title` and counts as
zero unblocked flow. Two equal-value active cards then sort by age, not
by live downstream flow — and because the banner truncates to
`active[:3]`, the wrong cards can even be the ones shown.

## Empirical evidence

`reproduce.py` builds four cards: `a1-active-two-live` (alice, active,
medium) advances two live open cards owned by bob; `a2-active-one-live`
(alice, active, medium, **older**) advances one. Both tie at value 5.1
on the full deck. Simulating `goc --worker alice`, the banner is built
from alice's cards only, so bob's downstream cards vanish from the
tiebreak lookup:

```
notice_cards (worker=alice): ['a1-active-two-live', 'a2-active-one-live']
ACTIVE: 2 claimed cards ...: a2-active-one-live, a1-active-two-live ...
```

`a2` (one live downstream) ranks ahead of `a1` (two) — the tie collapses
to the older card. Threading the full-deck `by_title` restores the
correct order (`a1` first), matching the documented tiebreak rationale.

## Why it matters

The active-card banner is a "before you claim work" hint a worker reads
on every `goc --worker <name>` and `GOC_WORKER`-scoped queue view. When
it mis-orders (or, past three cards, mis-selects) the claimed cards it
surfaces, it points the next worker at lower-leverage in-flight work
first. Low contribution — it is display ordering of a capped banner, not
queue correctness — but it is a clean api-contract regression: the lone
`sort_default` caller that still bakes its tiebreak lookup from a
caller-supplied subset.

## Fix

Give `render_active_notice` an optional `by_title` parameter (mirroring
`render_leverage_line` / `render_table` / `render_board`) and thread it
into `sort_default`; fall back to building it from `cards` only when the
caller omits it. Pass `full_by_title` from `_cmd_default` (it already
holds the full-deck lookup). No behavior change in the non-`--worker`
path, where `cards` was already the full deck.
