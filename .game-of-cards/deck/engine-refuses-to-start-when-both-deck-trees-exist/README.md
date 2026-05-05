---
title: engine-refuses-to-start-when-both-deck-trees-exist
summary: "After the 2026-05-05 migration, `_resolve_deck_dir` silently prefers `.game-of-cards/deck/` when both it and legacy `deck/` exist. Two `goc` clients writing to different trees (e.g., a stale uv-tool install and `uv run goc` from source) drifted in parallel for 12h before a human noticed. Make the engine refuse to operate (or require explicit migration) when both deck trees exist, so the dual-tree drift incident cannot recur silently."
status: done
stage: null
contribution: medium
created: 2026-05-05
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `_resolve_deck_dir` (or its caller) detects when both `.game-of-cards/deck/` and `deck/` exist and exits with a clear error pointing at a remediation path
  - [x] A `goc migrate` (or equivalent) verb performs the legacy-to-canonical merge with confirmation, including drift-detection across same-named cards
  - [x] The error message names both paths and tells the user how to resolve (run `goc migrate`, or delete the stale tree)
  - [x] Tests cover: only-canonical (passes), only-legacy (passes with deprecation), both-present (fails with actionable error), migration command (resolves drift)
  - [x] Docs explain the failure mode, why dual-tree drift was a real incident, and how to recover
  - [x] `uv run goc validate` passes
---

# Engine refuses to start when both deck trees exist

## Why

The 2026-05-05 deck migration (`9fa3a24`) created `.game-of-cards/deck/` but kept legacy `deck/` in place as a "compatibility fallback". `_resolve_deck_dir` chose canonical-when-present, legacy-otherwise — internally consistent, but it hides the failure mode where **two clients disagree on which path is canonical**.

That failure mode actually happened: a `uv tool install` of `goc` 0.0.3 (legacy-first) coexisted with `uv run goc` 0.0.4 from repo source (canonical-first). Both wrote, both committed, both validated. Drift was invisible until a human ran `diff -rq deck/ .game-of-cards/deck/` 12 hours later. Reconciled in commit `004756d`.

## What's broken

Compatibility fallbacks are silent by design. When two trees exist, the engine has no way to know which one a writer was *intending* to operate on, so it can't warn. The only safe behavior with two trees is to refuse.

## Fix shape

When `_resolve_deck_dir` is called and both paths exist:

1. Print an error naming both paths.
2. Suggest `goc migrate` (or `rm -rf <stale>`) as remediation.
3. Exit non-zero — do not pick a winner.

Add `goc migrate` that:

- Detects per-card drift (status, DoD, body content).
- Merges legacy → canonical with conflict reporting (refuse to silently overwrite differing files).
- Removes legacy `deck/` only after a clean merge.

## Notes

This is the systemic fix for the dual-tree drift incident. Compatibility lookup should remain for **one-tree** scenarios (legacy-only or canonical-only); only the both-trees case is fatal.
