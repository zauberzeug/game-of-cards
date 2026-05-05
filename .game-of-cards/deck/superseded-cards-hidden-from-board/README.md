---
title: superseded-cards-hidden-from-board
summary: "`goc --board` silently omits cards with the valid `superseded` status because the board renderer never creates a SUPERSEDED column."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] reproduce.py exits zero (superseded cards appear on the board)
  - [x] `goc --board` renders a SUPERSEDED column for full-board views
  - [x] Existing board columns for open/active/blocked/done/disproved still render
  - [x] `goc validate` passes after the board fix
---

# superseded-cards-hidden-from-board

## Location

`goc/engine.py:786` hard-codes the board columns.

## What's broken

`superseded` is a valid status in `goc/schema.yaml`, and the `status`
command can set it. The board renderer does not include that status:

```python
columns = ["open", "active", "blocked", "done", "disproved"]
```

Cards with `status: superseded` are ignored by the `if t.status in by_status`
guard and disappear from `goc --board`.

## Empirical evidence

A temporary deck containing one `status: superseded` card renders only:

```text
OPEN | ACTIVE | BLOCKED | DONE | DISPROVED
```

The `superseded-card` title is absent from the board output.

## Why it matters

The board is supposed to be the whole kanban view. Hiding a valid terminal
state makes superseded work look missing and breaks the expectation that
`goc --board` agrees with status-filtered deck queries.

## Fix

Add `superseded` to the board column list and cover it with a focused CLI
test so future status additions do not silently disappear.
