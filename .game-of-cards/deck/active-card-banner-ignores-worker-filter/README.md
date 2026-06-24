---
title: active-card-banner-ignores-worker-filter
summary: "`goc --worker <name>` scopes the open queue to one worker, but the `ACTIVE:` heads-up banner above the table is built from the full unfiltered deck — so it lists every worker's claimed cards, not just the filtered worker's. The board path one branch up already honors `--worker`; the table-banner call site does not."
status: done
stage: null
contribution: medium
created: "2026-06-24T02:26:20Z"
closed_at: "2026-06-24T02:30:55Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py builds a deck with one active card owned by `alice` and one by `bob`, runs the table render with `worker="alice"`, and asserts the `ACTIVE:` banner names only alice's card (exits zero on the fixed engine)
  - [x] TDD: a regression test in `tests/` asserts the worker-scoped banner behavior (and that an unfiltered run still lists all active cards)
  - [x] MECHANICAL: the `cli()` table branch in `goc/engine.py` passes a `--worker`-scoped card list to `render_active_notice`, mirroring the board path's `args.worker` handling
worker: {who: "claude[bot]", where: main}
---

# active-card-banner-ignores-worker-filter

## Location

`goc/engine.py:3477` (the `cli()` table-render branch).

## What's broken

The `ACTIVE:` heads-up banner — the "you have claimed cards outside this
open queue, check before claiming new work" coordination hint — is built
from the full, unfiltered card list, ignoring `--worker`:

```python
out = render_table(filtered, verbose=args.verbose, no_color=args.no_color, values=full_values, by_title=full_by_title)
active_notice = render_active_notice(cards, values=full_values) if status == "open" else ""
```

`cards` here is the whole deck. `render_active_notice`
(`goc/engine.py:3048-3071`) then unconditionally selects every active
card — it has no filter awareness:

```python
active = sort_default(
    [t for t in cards if t.status == "active"],
    ...
)
```

The board path, one branch up at `goc/engine.py:3463`, *does* honor the
worker filter:

```python
board_cards = filtered if (status_filter_explicit or args.worker) else cards
```

So `goc --worker alice` narrows the open queue (and the board) to alice,
but the table's banner still lists bob's and everyone else's claimed
cards. The banner is a *per-queue* "before you claim work" hint, and
`--worker` is exactly what defines whose queue it is — listing other
workers' claimed cards defeats its purpose and contradicts the board's
own behavior on the identical flag.

## Empirical evidence

See [reproduce.py](reproduce.py), which drives the real CLI against a
temp deck holding `alice-active`, `bob-active` (both `status: active`),
and `alice-open`. On the **unfixed** engine, `goc --worker alice`
produced:

```
ACTIVE: 2 claimed cards outside this open queue: alice-active, bob-active. ...
banner mentions bob-active:   True   (BUG if True)
```

On the **fixed** engine it is correctly worker-scoped:

```
ACTIVE: 1 claimed card outside this open queue: alice-active. ...
banner mentions bob-active:   False
banner mentions alice-active: True
PASS: ACTIVE banner is scoped to --worker alice.
```

The unfiltered run (`goc` with no `--worker`) still lists both active
cards, as asserted by `tests/test_active_notice_worker_scope.py`.

## Why it matters

`--worker` and `GOC_WORKER` exist precisely to give a runner a
worker-scoped queue view (per AGENTS.md's `worker` field section). The
autonomous `pull-card` loop reads the `ACTIVE:` banner as its
"is someone already on adjacent work?" soft-lock signal. When the banner
ignores `--worker`, a worker-scoped runner sees every other worker's
active cards as if they were its own collisions — noise that undercuts
the exact coordination the banner is for. The inconsistency is reachable
on any multi-worker deck: `cli()` (`render` path) passes the unfiltered
`cards` to `render_active_notice` whenever `--worker` is set with no
explicit status filter.

## Fix

At `goc/engine.py:3477`, pass a worker-scoped list to
`render_active_notice` when `args.worker` is set, mirroring the board's
`args.worker` handling at line 3463 and reusing the same `_worker_who`
match `filter_cards` uses:

```python
notice_cards = (
    [t for t in cards
     if args.worker.lower() in _worker_who(t.frontmatter.get("worker")).lower()]
    if args.worker else cards
)
active_notice = render_active_notice(notice_cards, values=full_values) if status == "open" else ""
```

Scope is deliberately limited to `--worker` (gate-free: the board sets
the precedent). Whether the banner should also honor `--tag` /
`--contribution` / `--human-gate` is a separate, debatable call — the
banner is arguably a global reminder for those — and is out of scope for
this card.
