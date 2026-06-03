---
title: board-columns-hardcoded-instead-of-derived-from-schema-status-values
status: active
stage: null
contribution: medium
created: "2026-06-03T05:06:44Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] EMPIRICAL: `reproduce.py` shows a card whose `status` is not in the
        hardcoded list is silently dropped from `render_board` before the fix,
        and appears after.
  - [ ] `render_board` derives its columns from `load_schema().status_values`
        instead of the hardcoded `["open","active","blocked","done","disproved","superseded"]`.
  - [ ] Behavior-preserving for the shipped schema: board output is byte-identical
        for the current six-status enum (same column set, same order).
  - [ ] TDD: a regression test asserts a card with a status outside the legacy
        hardcoded set still renders on the board.
  - [ ] `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green.
worker: {who: "claude[bot]", where: main}
---

# `render_board` hardcodes its status columns instead of deriving them from the schema

## Problem

`render_board` (`goc/engine.py:2562`) builds its kanban columns from a
literal list:

```python
columns = ["open", "active", "blocked", "done", "disproved", "superseded"]
by_status: dict[str, list[Card]] = {c: [] for c in columns}
...
for t in cards:
    if t.status in by_status:          # engine.py:2567
        by_status[t.status].append(t)
```

`schema.yaml` already declares the authoritative status enum:

```yaml
status_values: [open, active, blocked, done, disproved, superseded]
```

The board re-states that enum as a literal. The two are kept in sync
only by hand. Consequences:

1. **Silent card drop.** Any card whose `status` is not in the hardcoded
   list is dropped at `engine.py:2567` — it disappears from `goc --board`
   with no row and no diagnostic. The board reads as "complete" while
   omitting work.
2. **Single-source-of-truth violation.** The status enum lives in
   `schema.yaml`; the board duplicates it. The renderer should consume
   the schema, not mirror it.

## Reachability

`render_board` runs on the output of `load_all_cards()`, which loads
every card-shaped README **without** validating its `status` against the
schema (validation is `goc validate`, a separate verb). So the offending
input is produced by:

- A hand-edited or mid-migration card carrying a status not yet in the
  hardcoded list — the `remove-blocked-from-the-status-enum-and-validator`
  work changes this enum, and the board's literal will drift from it.
- The in-flight `support-custom-card-workflows-and-statuses` epic, which
  exists specifically to let a consuming repo define its own statuses in
  `schema.yaml`. Today those custom statuses would render on the table
  (`render_table` has no such hardcoded list) but vanish from the board.

## Evidence

See `reproduce.py`. A card with `status: review` (a plausible custom
workflow status) is present in the deck handed to `render_board` but
absent from the rendered board, while `schema.status_values` is the
list the renderer *should* have used.

## Fix

Derive `columns` from `load_schema().status_values`. The shipped schema's
order is identical to the current literal
(`[open, active, blocked, done, disproved, superseded]`), so the change is
byte-identical for today's enum and additionally renders any
schema-declared status (custom or post-migration). No decision is
required — the schema is by definition the source of truth for valid
statuses, and the board's desired column order is exactly the enum order.

## Why it matters

The board is the primary "make work visible" surface (Kanban first
practice). A renderer that can silently omit cards undermines that
guarantee, and the duplication is a latent break for two open epics that
both touch the status enum.
