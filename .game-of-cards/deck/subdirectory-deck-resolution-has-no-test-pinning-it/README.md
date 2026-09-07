---
title: subdirectory-deck-resolution-has-no-test-pinning-it
status: done
stage: null
contribution: medium
created: "2026-08-01T09:01:14Z"
closed_at: "2026-08-11T05:11:15Z"
human_gate: none
advances: []
advanced_by: []
tags: [infra]
summary: "CLOSED. `_resolve_deck_root` (`goc/engine.py:73`) resolves the deck by walking from cwd to the nearest ancestor carrying `.game-of-cards/`, shipped in 3e17e3b3 (2026-07-15). The card was filed claiming nothing pinned it; that was half wrong — `tests/test_new_resolves_existing_deck_root.py` shipped in the fix commit itself and pins the `goc new` WRITE path. The genuinely unpinned half was the READ path, which is where the reported consumer failure lives: readers below the deck root exited 0 with zero cards, indistinguishable from a drained deck. `tests/test_subdirectory_deck_resolution.py` now pins it — every aggregate reader from a nested subdirectory, plus the read-side foreign-git-tree boundary."
definition_of_done: |
  - [x] TDD: a test chdirs into a subdirectory of a fixture deck repo and pins, together, that `validate`, `quality-pass`, `--status all --json`, `--ready --json` and `show` all address the real deck (red against the pre-3e17e3b3 behavior, green at HEAD)
  - [x] TDD: the same suite pins the write half — `goc new` from a subdirectory files into the real deck and does not scaffold a nested `.game-of-cards/` under cwd
  - [x] TDD: the contract's boundary is pinned — the walk stops before an ancestor that is a different git working tree, and a mutating command outside any deck is refused rather than scaffolding at cwd
worker: {who: "claude[bot]", where: main}
---

# Subdirectory deck resolution has no test pinning it

`_resolve_deck_root` (goc/engine.py:73) resolves the deck by walking from
cwd to the nearest ancestor that carries `.game-of-cards/` — shipped in
3e17e3b3 ("fix: resolve new cards to existing deck root", 2026-07-15) with
a precise contract in its docstring: the walk may climb plain directories,
stops before entering a different git working tree, and mutating creation
commands must reject the cwd fallback instead of scaffolding a second deck.

The card was filed on the claim that *nothing* in `tests/` pinned this. That
claim was half wrong, and the correction is the useful part of this card:
`tests/test_new_resolves_existing_deck_root.py` shipped inside 3e17e3b3
itself and was extended by 30355095, pinning the `goc new` **write** path
across four cwd shapes. What no test covered was the **read** path — and
that is precisely where the reported consumer failure lives.

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

## Resolution

`tests/test_subdirectory_deck_resolution.py` (new, 3 tests) pins the
previously-uncovered halves. It runs the CLI as a subprocess with `cwd` set
below the deck root — the same technique its sibling module uses — because
`_resolve_deck_root` is driven by the process's working directory.

| Test | Pins |
|---|---|
| `test_readers_from_subdirectory_address_the_real_deck` | `validate`, `quality-pass`, `--status all --json`, `--ready --json` and `show` all address the root deck from `src/deep/nested/`, and no reader scaffolds a shadow `.game-of-cards/` beside itself |
| `test_new_from_subdirectory_files_into_the_repo_root_deck` | the write half in the shape the read half fails in — a plain subdirectory of the git repo that owns the deck at its root |
| `test_readers_in_a_nested_foreign_tree_do_not_inherit_the_enclosing_deck` | the read-side boundary: a vendored repo nested inside a deck-owning repo reads zero cards rather than its host's deck |

Both directions of the contract were verified red, not assumed:

- Against a resolver patched to `return cwd` (pre-3e17e3b3), the reader test
  fails on all three reader families — `--status all --json` and
  `--ready --json` return `[]` against an expected `['fixture-card']`, and
  `validate` prints nothing. That is the consumer's symptom reproduced
  exactly. The write test fails too, refusing with "no Game of Cards deck
  found".
- Against a resolver patched to skip the foreign-working-tree stop
  (pre-30355095), the boundary test fails the other way, inheriting
  `host-repo-card` across the tree line. So it is a live pin, not a
  tautology that any resolver satisfies.

The write-side boundary named in DoD item 3 — a *mutating* command below a
foreign tree or outside any deck must refuse rather than scaffold at cwd —
was already pinned by the sibling module
(`test_new_from_repo_nested_in_deck_owning_repo_refuses`,
`test_new_from_nested_worktree_refuses_without_shared_opt_in`,
`test_new_without_installed_deck_fails_without_writing`). Those were read
and re-run rather than duplicated; the new module covers the read-side half
of the same rule.

## Coverage map

The two modules are complementary, not overlapping — read them together:

- `tests/test_new_resolves_existing_deck_root.py` — the write path
  (`goc new`) across workspace, nested-repo, nested-worktree and
  no-deck-anywhere shapes.
- `tests/test_subdirectory_deck_resolution.py` — the read path from a
  subdirectory of the deck-owning repo, and the read-side tree boundary.
