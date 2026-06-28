---
title: advances-and-advanced-by-filters-default-open-only-hiding-closed-endpoints
status: open
stage: null
contribution: medium
created: "2026-06-28T01:55:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] DECISION: human picks whether `--advances` / `--advanced-by` (table view, no explicit `--status`) auto-extend to `all` like `--board`/`--waiting`/`--closed-since`, or stay open-only like `--worker` (record framing vs scheduler framing); decision recorded in log.md
  - [ ] TDD: reproduce.py reflects the chosen behavior (exit 1 if auto-extend is chosen and implemented; left as documented-intended if open-only is affirmed)
  - [ ] TDD: a regression test in tests/ pins the agreed contract for both edge filters
  - [ ] MECHANICAL: if auto-extend is chosen, `engine.py` `_cmd_default` extends the implicit-status condition; if open-only is affirmed, the `--advances`/`--advanced-by` help text documents that closed endpoints need `--status all`
---

# `--advances` / `--advanced-by` apply the open-only default, hiding closed relationship endpoints

## Summary

`goc --advances X` and `goc --advanced-by X` are relationship queries, but
with no explicit `--status` they inherit the open-only queue default, so any
edge endpoint that has since closed (done / disproved / superseded) silently
vanishes. A cold reader using the edge filter to walk the record axis sees a
truncated graph and cannot tell endpoints are missing.

## Location

`goc/engine.py:3531-3546` — the implicit-status default in `_cmd_default`:

```python
elif args.status_flag is None:
    # --waiting and --closed-since both surface cards beyond the open
    # queue (active-impeded cards, closed cards): auto-extend the default
    # status to "all" so the subsequent filter has something to narrow.
    # --board spans every status column by design; ...
    status = (
        "all"
        if (
            closed_since_threshold is not None
            or getattr(args, "waiting", False)
            or args.board
        )
        else "open"
    )
```

`args.advances` and `args.advanced_by` are **not** in the auto-extend
condition, so they fall through to `"open"`.

## What's broken

The auto-extend list names every filter whose purpose spans statuses
(`--closed-since`, `--waiting`, `--board`) but omits the two edge filters.
The edge filters are then passed straight into `filter_cards(..., status="open",
advances=..., advanced_by=...)`, which narrows to *open* endpoints before the
edge match is even considered.

This contradicts the record-axis contract in `AGENTS.md`:

> The deck is both a scheduler and a record. ... the record axis walks
> edges that include closed cards so a cold reader can reconstruct the
> history of a decision. Closed-card relationship edges are first-class ...

An explicit `--advanced-by X` is the most natural CLI expression of that
record-axis walk, yet it returns only the open slice.

## Empirical evidence

`reproduce.py` builds a temp deck with a closed parent ↔ closed child edge
pair and queries both directions:

```
--advances synthetic-closed-parent-card              -> []
--advances synthetic-closed-parent-card --status all -> ['synthetic-closed-child-card']
--advanced-by synthetic-closed-child-card              -> []
--advanced-by synthetic-closed-child-card --status all -> ['synthetic-closed-parent-card']

DEFECT FIRES: an explicit edge filter dropped a CLOSED relationship endpoint that --status all surfaces.
```

The default returns nothing; only `--status all` surfaces the closed endpoint.

## Why it matters

Reachability: any deck where a relationship endpoint closes while the other
side stays open (an epic whose children close one by one; a card superseded
by one that later closes) produces this. The live deck already does — e.g.
`goc --advanced-by provide-claude-code-plugin-for-skills-and-hooks` returns
nothing under the default but three cards (`active`/`done`) under `--status all`.

The closest precedent,
[board-worker-filter-hides-active-cards-by-applying-open-only-default](../board-worker-filter-hides-active-cards-by-applying-open-only-default/),
was filed as a `bug`/`api-contract` defect and fixed by adding `args.board`
to this exact condition — establishing that "open-only default leaking into a
status-spanning view" is a recognized defect class here. That fix, however,
deliberately extended only the **board** path and left `--worker` table views
open-only (DoD item: "The contested `board_cards = ...` gate line is left
untouched"). So the edge filters are not an open-and-shut instance — see the
decision below.

## Decision required

Should the edge filters auto-extend, or stay open-only?

**Option A — auto-extend (record-axis-first).** Add `args.advances` /
`args.advanced_by` to the `_cmd_default` condition so a bare `goc --advanced-by X`
spans every status, matching `--board`/`--waiting`/`--closed-since`. Pro: the
edge filter then honors the deck-as-record contract; "show me everything wired
to X" works without remembering `--status all`. Con: a user wanting only the
*open* children of an epic (a scheduler-axis prioritization view) must now add
`--status open`, and closed cards clutter that view.

**Option B — affirm open-only (scheduler-axis-first).** Treat the edge filters
like the `--worker` table view, which the board-worker fix intentionally left
open-only: the default is the actionable scheduler slice, and the record-axis
walk is `--status all --advanced-by X`. Pro: no behavior change; consistent
with `--worker`. Con: the omission stays a discoverability trap; document it in
the `--advances`/`--advanced-by` help text so the truncation is not silent.

The two precedents pull opposite ways (cross-status `--board` vs open-only
`--worker`), which is why this needs a human pick rather than a rubric
derivation. Whichever is chosen, the help text and a regression test should
pin it so the next reader is not surprised.
