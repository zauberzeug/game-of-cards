---
title: board-drops-cards-whose-status-is-outside-the-schema-enum
status: open
stage: null
contribution: medium
created: "2026-06-25T20:20:50Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`render_board` files cards into columns keyed solely by the schema's status enum and drops any card whose status is not one of those keys — no column, no diagnostic, not counted in the `… +N more` overflow. `render_table` (the default view) keeps the card, so the two human-facing renderers disagree about which cards exist, and the board's own comment claims it `never silently drops a card`."
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (board surfaces an off-enum card; defect no longer fires)
  - [ ] TDD: a regression test asserts a card whose status is outside `schema.status_values` appears in `render_board` output, mirroring `test_board_columns_derive_from_schema_status_values`
  - [ ] MECHANICAL: `render_board` renders off-enum statuses as extra trailing columns (first-seen order) so every card the table shows, the board shows too
  - [ ] MECHANICAL: behavior-preserving for the shipped six-status enum (no output diff when every card's status is in the enum)
  - [ ] PROCESS: `uv run goc validate` passes and `uv run python -m unittest discover -s tests` is green
---

# Board drops cards whose status is outside the schema enum

## Location

`goc/engine.py:2992-2998` (inside `render_board`).

## What's broken

`render_board` builds its column map exclusively from the schema's
status enum, then files each card into that map — dropping any card
whose status is not a key:

```python
columns = list(load_schema().status_values)
by_status: dict[str, list[Card]] = {c: [] for c in columns}
if by_title is None:
    by_title = {t.title: t for t in cards}
for t in cards:
    if t.status in by_status:
        by_status[t.status].append(t)
    # else: card is silently discarded — no column, no diagnostic,
    #       and not counted in any `… +N more` overflow indicator.
```

The block comment immediately above this code asserts the opposite:

```python
# Columns derive from the schema's status enum — the single source of
# truth — not a hardcoded literal. This keeps the board in lockstep with
# `status_values` (custom workflows, enum migrations) and never silently
# drops a card whose status the renderer "forgot" to list.
```

The comment is right about the *column source* (it derives from the
schema, fixed by the closed card
[board-columns-hardcoded-instead-of-derived-from-schema-status-values](../board-columns-hardcoded-instead-of-derived-from-schema-status-values/)),
but wrong about the *drop*: a card whose status is not in the enum is
silently discarded. By contrast `render_table`
(`goc/engine.py:2804`) iterates `for t in cards` and emits a row for
every card regardless of status. The two human-facing renderers
disagree about which cards exist.

## Empirical evidence

```
schema enum: ['open', 'active', 'done', 'disproved', 'superseded']
legacy-blocked in BOARD? False
legacy-blocked in TABLE? True
```

A card with `status: blocked` and a schema enum that no longer lists
`blocked` vanishes from `goc --board` but stays in the default `goc`
table. See `reproduce.py`.

## Why it matters

The reachability path is live in this very repo. There is an
in-flight family of cards to remove `blocked` from the status enum
([remove-blocked-from-status-enum-and-migrate-existing-cards](../remove-blocked-from-status-enum-and-migrate-existing-cards/),
[remove-blocked-from-the-status-enum-and-validator](../remove-blocked-from-the-status-enum-and-validator/)).
The instant `blocked` is deleted from `schema.yaml`, every existing
`status: blocked` card disappears from `goc --board` — precisely the
cards an operator needs the board to surface so they can be migrated.
The same hole hits any custom-workflow enum that later drops a status
and any hand-edited or typo'd status. `goc validate` flags an
off-enum status as an error, but the board is a read view that should
*show* the broken card (the way `render_table` does), not hide it.

This is distinct from the closed meta-fix
[schema-enum-surfaces-keep-drifting-into-hardcoded-literals](../schema-enum-surfaces-keep-drifting-into-hardcoded-literals/):
that family eliminated hardcoded enum *literals* by deriving columns
from the schema. This card is the residual silent-drop class for
statuses outside the schema enum — a different defect the column-derive
fix did not address.

## Fix

In `render_board`, after building `by_status` from the schema enum,
collect any statuses present in `cards` but absent from the enum (in
first-seen order) and append them as extra trailing columns before the
per-column sort/overflow loop. This mirrors `render_table`'s
"show everything" contract and makes the existing block comment true.
Rendering each off-enum status under its own labelled column (rather
than one merged "OTHER" bucket) keeps the board's column-per-status
model intact and shows the operator exactly which legacy status the
straggler carries.
