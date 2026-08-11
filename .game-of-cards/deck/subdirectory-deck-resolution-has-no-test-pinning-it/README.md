---
title: subdirectory-deck-resolution-has-no-test-pinning-it
status: open
stage: null
contribution: medium
created: "2026-08-01T09:01:14Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra]
summary: "`_resolve_deck_root` (`goc/engine.py:73`) resolves the deck by walking from cwd to the nearest ancestor carrying `.game-of-cards/`, under a precise docstring contract — climb plain directories, stop before a different git working tree, refuse the cwd fallback for mutating creation commands — shipped in 3e17e3b3 (2026-07-15). No test in `tests/` references the function or chdirs below a fixture deck root, so the behavior every aggregate reader depends on is pinned by nothing. The pre-fix failure was not hypothetical: a consumer repo's refine pass read an empty-because-unresolved deck as a drained one, because every reader exits 0 with zero cards."
definition_of_done: |
  - [ ] TDD: a test chdirs into a subdirectory of a fixture deck repo and pins, together, that `validate`, `quality-pass`, `--status all --json`, `--ready --json` and `show` all address the real deck (red against the pre-3e17e3b3 behavior, green at HEAD)
  - [ ] TDD: the same suite pins the write half — `goc new` from a subdirectory files into the real deck and does not scaffold a nested `.game-of-cards/` under cwd
  - [ ] TDD: the contract's boundary is pinned — the walk stops before an ancestor that is a different git working tree, and a mutating command outside any deck is refused rather than scaffolding at cwd
---

# Subdirectory deck resolution has no test pinning it

`_resolve_deck_root` (goc/engine.py:73) resolves the deck by walking from
cwd to the nearest ancestor that carries `.game-of-cards/` — shipped in
3e17e3b3 ("fix: resolve new cards to existing deck root", 2026-07-15) with
a precise contract in its docstring: the walk may climb plain directories,
stops before entering a different git working tree, and mutating creation
commands must reject the cwd fallback instead of scaffolding a second deck.

No test in `tests/` references the function or chdirs below a fixture deck
root: the behavior every aggregate reader depends on is pinned by nothing.

## Why it matters

The pre-fix behavior was not hypothetical: a consumer filed
`deck-commands-run-from-a-subdirectory-report-a-healthy-empty-deck`
(zauberzeug/zoe-app deck, 2026-07-31) after a refine pass took an
empty-because-unresolved deck for a clean one — every reader exits 0 with
zero cards, which is indistinguishable from a drained deck. Their
`reproduce.sh` is an end-to-end consumer pin (red against the pre-fix
engine still shipped in the `zauberzeug-claude` marketplace 0.0.27 bundle,
green at HEAD — same version string, see
[zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases](../zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases/)) —
but it lives downstream and guards nothing in this repo's CI.

## Fix

One test module with a fixture deck: chdir into a nested directory and pin
the read half (all aggregate readers see the fixture card), the write half
(`goc new` files into the real deck, no shadow `.game-of-cards/`), and the
contract's boundary (foreign-git-tree stop; mutating command outside any
deck refuses). Red/green is available by running against the pre-3e17e3b3
engine.
