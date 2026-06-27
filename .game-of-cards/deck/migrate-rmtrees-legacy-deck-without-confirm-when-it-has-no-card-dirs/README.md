---
title: migrate-rmtrees-legacy-deck-without-confirm-when-it-has-no-card-dirs
summary: "`goc migrate` only runs its confirm prompt inside `if to_copy or identical:`. When the legacy `deck/` holds no card subdirectories (only loose files like `.goc-version`, `README.md`, notes) but a canonical tree also exists, both lists are empty, the early return is suppressed by the dual-tree-conflict guard, the confirm gate is skipped entirely, and `shutil.rmtree(legacy)` deletes the loose files unconditionally — no prompt, no `--auto-yes`."
status: open
stage: null
contribution: medium
created: "2026-06-27T02:07:34Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — with a dual-tree state whose legacy `deck/` has no card subdirectories, `goc migrate` (no `--auto-yes`, empty stdin) does NOT delete the legacy tree.
  - [ ] TDD: regression test asserts `confirm()` is invoked before `rmtree` on the no-card-dirs fall-through path, and that declining (`n`) leaves the legacy tree intact.
  - [ ] TDD: existing migrate behavior preserved — the `to_copy`/`identical` confirm path and the `--auto-yes` skip-prompt path still work.
  - [ ] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green).
---

# `goc migrate` rmtrees the legacy deck/ without confirming when it has no card dirs

`goc migrate`'s confirmation prompt — the one guard before a destructive
`shutil.rmtree(legacy)` — is nested inside `if to_copy or identical:`. When the
legacy `deck/` contains **no card subdirectories** (only loose files), both
lists are empty, so the prompt is skipped and the tree is deleted with no
confirmation and without `--auto-yes`.

## Location

- `goc/engine.py:5918-5921` — `if not to_copy and not identical:` prints
  "nothing to migrate", but the early `return` is gated on
  `not dry_run and not _DUAL_TREE_CONFLICT` — so in a dual-tree conflict it does
  NOT return.
- `goc/engine.py:5934-5937` — the confirm gate lives inside
  `if to_copy or identical:`, which is `False` on this path.
- `goc/engine.py:5943` — `shutil.rmtree(legacy)` then runs unconditionally.

## What's broken

```python
    if not to_copy and not identical:
        print("Legacy deck/ contains no card directories; nothing to migrate.")
        if not dry_run and not _DUAL_TREE_CONFLICT:
            return                       # suppressed when _DUAL_TREE_CONFLICT
    ...
    if to_copy or identical:             # False -> confirm gate skipped
        if not auto_yes:
            if not confirm(f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?"):
                sys.exit(1)
    ...
    shutil.rmtree(legacy)                # runs anyway -> deletes loose files
```

`confirm()` (`engine.py:3189`) in non-tty mode returns its `default` (False) on
empty input, so if the gate *had* fired with no input the migrate would have
aborted (exit 1) and the loose files would survive. Instead the output even
contradicts itself: it prints "nothing to migrate" and then "Removed legacy
tree" in the same run.

## Empirical evidence

`uv run python .game-of-cards/deck/migrate-rmtrees-legacy-deck-without-confirm-when-it-has-no-card-dirs/reproduce.py`:

```
before: legacy deck/ exists: True
before: NOTES.txt exists:    True

--- migrate stdout ---
Legacy deck/ contains no card directories; nothing to migrate.

Removed legacy tree: /tmp/tmpyxsb3h92/repo/deck
Migration complete. Run `goc validate` to confirm.
Next: `goc validate` to verify card integrity after migration.
--- exit=0 ---

after: legacy deck/ removed:    True
after: NOTES.txt destroyed:     True
confirm prompt shown to user:   False

DEFECT CONFIRMED: `goc migrate` deleted the legacy deck/ and its loose files with no confirmation prompt and without --auto-yes.
```

## Why it matters

Reachability: the dual-tree-conflict state (`_DUAL_TREE_CONFLICT = True`, set in
`_resolve_deck_dir` when both `.game-of-cards/deck/` and `deck/` exist) is the
*expected* precondition for `goc migrate` — it's the remediation the engine
prints for the conflict. A legacy `deck/` whose card subdirectories were already
moved to the canonical tree but still holds its sentinel (`deck/.goc-version`)
and other loose files (a `README.md`, notes, a partial migration) is a real GoC
legacy deck by any deck-identity predicate, and on `goc migrate` it is deleted
without ever prompting. The loose files are gone with no chance to decline.

This is the confirm-*gate-bypass* facet of the migrate data-loss family. It is
orthogonal to the deck-identity-predicate decision in
[unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it](../unrelated-deck-folder-trips-dual-tree-refusal-and-migrate-deletes-it/)
(which asks *whether* a `deck/` is a card deck at all) and to the un-copied-file
deletion in
[goc-migrate-silently-destroys-card-files-other-than-readme-and-log](../goc-migrate-silently-destroys-card-files-other-than-readme-and-log/)
(which deletes files *inside* migrated card dirs). Regardless of how those land,
a destructive `rmtree` should never run without confirmation.

## Fix

Move the confirm gate so it covers every non-dry-run path that reaches
`rmtree`, including the empty-`legacy_dirs` fall-through. When there are no
cards to migrate, the prompt names the loose-file removal instead of a card
count:

```python
    if not auto_yes:
        if to_copy or identical:
            prompt = f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?"
        else:
            prompt = (
                f"\nLegacy deck/ has no card directories but still contains files.\n"
                f"Remove legacy tree {legacy}?"
            )
        if not confirm(prompt):
            sys.exit(1)
```

The non-dual-tree empty case still early-returns at line 5920 (no deletion), so
the only path reaching this new prompt with empty lists is the dual-tree
conflict — exactly the destructive case that needs the gate.
