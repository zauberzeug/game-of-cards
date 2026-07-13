---
title: invalid-since-date-silently-empties-done-query
summary: "`goc --done --since nope` exits successfully with an empty result because the date filter is treated as an unchecked string."
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
  - [x] reproduce.py exits zero (invalid `--since` values are rejected)
  - [x] `goc --done --since nope` exits with a concise Click validation error
  - [x] Valid `YYYY-MM-DD` `--since` filters still return matching done cards
  - [x] `goc validate` passes after the filter validation fix
---

# invalid-since-date-silently-empties-done-query

## Location

`goc/engine.py:852` accepts `--since` as an unchecked string, and
`goc/engine.py:561` compares it lexically against `closed_at`.

## What's broken

The help text says `--since` is a date filter for done cards. Invalid dates
currently pass through as ordinary strings:

```bash
goc --done --since nope
```

That exits 0 with no output, which looks like "no recent done cards" instead
of "bad date".

## Empirical evidence

Before the fix, `uv run goc --done --since nope` exits 0 and prints nothing.

## Why it matters

Release and throughput checks depend on done-card date filters. A typo in the
date should be surfaced as CLI usage error rather than silently changing the
query result.

## Fix

Validate `--since` as `YYYY-MM-DD` at the Click boundary and keep the internal
filter value as an ISO date string so existing lexical date comparisons remain
valid.
