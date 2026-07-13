---
title: invalid-tag-filter-silently-empties-queue
summary: "`goc --tag not-a-real-tag` exits successfully with an empty queue even though tags are canonical schema values elsewhere."
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
  - [x] reproduce.py exits zero (invalid read-only tag filters are rejected)
  - [x] `goc --tag not-a-real-tag` exits with a concise Click validation error
  - [x] Valid built-in and project-extended tag filters still render matching cards
  - [x] `goc validate` passes after the filter validation fix
---

# invalid-tag-filter-silently-empties-queue

## Location

`goc/engine.py:855` accepts repeated read-only `--tag` filters without
checking them against `load_schema().canonical_tags`.

## What's broken

`goc new --tag ...` and `goc validate` reject unknown tags, but read-only
queue filtering does not:

```bash
goc --tag not-a-real-tag
```

That exits 0 with no rows, which looks like a valid empty queue instead of a
typoed tag.

## Empirical evidence

Before the fix, `uv run goc --tag not-a-real-tag` exits 0 and prints nothing.

## Why it matters

Autonomous and human triage often filter by tag. A typo should fail visibly
because otherwise a real queue can look empty.

## Fix

Validate supplied tag filters against the same canonical tag set used by card
creation and deck validation, including project-local tag extensions from
`.game-of-cards/canonical-tags.md`.
