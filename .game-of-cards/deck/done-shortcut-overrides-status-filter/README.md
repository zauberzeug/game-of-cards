---
title: done-shortcut-overrides-status-filter
summary: "`goc --done --status open` silently ignores the explicit status filter and returns done cards because the shortcut wins without validation."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-04
human_gate: none
advances:
  - query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] reproduce.py exits zero (`--done` and `--status` can no longer conflict silently)
  - [x] `goc --done --status open` exits with a concise usage error
  - [x] `goc --done` and `goc --status done` still return done cards
  - [x] `goc validate` passes after the filter conflict fix
---

# done-shortcut-overrides-status-filter

## Location

`goc/engine.py:892` gives `--done` priority over `--status` without checking
whether the user passed both.

## What's broken

`--done` is documented as a shortcut for `--status done`, but it can be
combined with a contradictory explicit status:

```bash
goc --done --status open
```

That exits 0 and returns done cards, silently ignoring `--status open`.

## Empirical evidence

Before the fix, `uv run goc --done --status open` prints the same done-card
table as `uv run goc --done`.

## Why it matters

Conflicting filters should be explicit usage errors. Silent precedence makes
automation and humans trust the wrong query.

## Fix

Reject invocations that pass both `--done` and `--status`. Keep each form
working independently.
