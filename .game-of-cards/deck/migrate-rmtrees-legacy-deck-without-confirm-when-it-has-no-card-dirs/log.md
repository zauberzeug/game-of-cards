## 2026-06-27 — filed and fixed (fix-through)

Surfaced during an empty-queue audit pass. Confirmed via reproduce.py that
`goc migrate` deleted a dual-tree legacy `deck/` holding only loose files
(`.goc-version`, `NOTES.txt`) with no confirm prompt and without `--auto-yes`.

Root cause: the confirm gate was nested inside `if to_copy or identical:`
(`engine.py:5934`), which is `False` when `legacy_dirs` is empty. The non-dual-tree
empty case early-returns at line 5920, but a dual-tree conflict suppresses that
return and falls straight through to `shutil.rmtree(legacy)`.

Fix: hoisted the confirm gate to cover every non-dry-run path reaching `rmtree`.
When there are no cards to migrate, the prompt names the loose-file removal
("Legacy deck/ has no card directories but still contains files. Remove legacy
tree ...?") instead of a card count. The non-conflict empty case still returns
early, so the new empty-list prompt is only reachable in a dual-tree conflict —
exactly the destructive case.

Regression: added `test_migrate_confirms_before_removing_legacy_with_no_card_dirs`
(declined confirm leaves the tree + loose files intact) and
`test_migrate_auto_yes_removes_legacy_with_no_card_dirs` (--yes still removes it)
to `tests/test_install.py`. Full suite 627 passing; plugin mirrors re-synced.
