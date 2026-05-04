---
title: invalid-status-filter-silently-empties-queue
summary: "`goc --status bogus` exits successfully with an empty queue because the read-only status filter is not validated against the status enum."
status: active
stage: null
contribution: medium
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] reproduce.py exits zero (invalid read-only status filters are rejected)
  - [ ] `goc --status bogus` exits with a concise Click validation error
  - [ ] Valid status filters, including `all`, still render matching cards
  - [ ] `goc validate` passes after the filter validation fix
---

# invalid-status-filter-silently-empties-queue

## Location

`goc/engine.py:854` accepts the read-only `--status` filter as an unchecked
string.

## What's broken

The mutating `goc status <title> <new_status>` command uses a Click choice,
but the queue filter does not. Invalid filters pass through:

```bash
goc --status bogus
```

That exits 0 and prints no rows, which looks like a valid empty queue instead
of bad input.

## Empirical evidence

Before the fix, `uv run goc --status bogus` exits 0 and prints nothing.

## Why it matters

The deck status lifecycle is an enum. Read-only filters should fail fast when
the operator mistypes the status; otherwise the CLI can hide work behind an
empty result.

## Fix

Use a Click choice for read-only status filters with the lifecycle statuses
plus the special `all` filter. Keep `goc --status all` and ordinary status
filters working.
