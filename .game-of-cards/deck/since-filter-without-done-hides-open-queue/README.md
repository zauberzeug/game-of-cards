---
title: since-filter-without-done-hides-open-queue
summary: "`goc --since YYYY-MM-DD` without `--done` applies a closed-date filter to the default open queue and returns no rows instead of reporting an invalid filter combination."
status: done
stage: null
contribution: medium
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] reproduce.py exits zero (`--since` without a done-status query no longer hides open cards)
  - [x] `goc --since 2026-05-04` exits with a concise usage error, or explicitly implies the done-card query
  - [x] `goc --done --since 2026-05-04` and `goc --status done --since 2026-05-04` still work
  - [x] `goc validate` passes after the filter-combination fix
---

# since-filter-without-done-hides-open-queue

## Location

`goc/engine.py` documents `--since` as "With --done", but the root command
accepts it independently and passes it into `filter_cards` for whatever status
is active.

## What's broken

The default queue is `status: open`. Open cards do not have `closed_at`, so:

```bash
goc --since 2026-05-04
```

exits 0 and prints no rows, even when open cards exist. The CLI silently
applies a done-card date filter to the open queue.

## Empirical evidence

The reproducer creates a temporary deck with one open card, runs
`goc --since 2026-05-04`, and observes exit 0 with the open card absent.

## Why it matters

Operators use the default queue for "what is open?" and `--since` for done-card
throughput. Combining them accidentally should not make the open queue look
empty.

## Fix

Pick one explicit contract and encode it:

- preferred: reject `--since` unless the effective status is `done`;
- acceptable: make `--since` imply the done-card query.

Whichever contract is chosen, add regression coverage for the bare `--since`
case and for the valid done-card date-filter cases.
