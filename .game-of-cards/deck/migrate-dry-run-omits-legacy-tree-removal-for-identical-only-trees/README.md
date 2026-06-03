---
title: migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees
summary: "`goc migrate --dry-run` only previews the legacy-tree deletion when there are legacy-only cards to copy (`to_copy`) or the legacy dir is empty. When every legacy card is identical to its canonical counterpart (`to_copy == []`, `identical` non-empty), the dry-run hides the `Would remove legacy tree` line even though the real run unconditionally `rmtree`s the legacy tree — defeating the purpose of `--dry-run` for the one case where the only effect is a deletion."
status: active
stage: null
contribution: medium
created: "2026-06-03T04:51:16Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — `goc migrate --dry-run` on an identical-only legacy tree prints a `Would remove legacy tree` line
  - [ ] TDD: regression test asserts the dry-run preview includes the removal line when `to_copy == []` and `identical` is non-empty
  - [ ] MECHANICAL: the dry-run guard at `engine.py` fires whenever the real run would reach `rmtree(legacy)` (i.e. includes the `identical` case)
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes
  - [ ] PROCESS: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc migrate --dry-run` hides the legacy-tree deletion for identical-only trees

## Location

`goc/engine.py` — `_cmd_migrate`, the dry-run preview block at
`engine.py:5079-5083`, contrasted with the real-run deletion at
`engine.py:5094`.

## What's broken

`_cmd_migrate` partitions legacy card dirs into `to_copy`
(legacy-only) and `identical` (present in both trees, `README.md` /
`log.md` byte-match). The **real run** unconditionally deletes the
whole legacy tree once it passes the confirm gate:

```python
    if to_copy or identical:
        if not auto_yes:
            if not confirm(f"\nMigrate {len(to_copy)} card(s) and remove legacy deck/?"):
                sys.exit(1)

    for name in to_copy:
        shutil.copytree(str(legacy_dirs[name]), str(canonical / name))
        print(f"  migrated: {name}")

    shutil.rmtree(legacy)            # engine.py:5094 — always reached here
    print(f"\nRemoved legacy tree: {legacy}")
```

But the **dry-run preview** only announces that deletion when there
are legacy-only cards to copy, or the legacy dir is empty:

```python
    if dry_run:
        if to_copy or not legacy_dirs:          # engine.py:5080 — omits `identical`
            print(f"Would remove legacy tree: {legacy}")
        print("Dry run — no changes made.")
        return
```

When every legacy card is identical to canonical
(`to_copy == []`, `legacy_dirs` non-empty), the guard evaluates to
`False or (not <non-empty>)` → `False`, so the `Would remove legacy
tree` line is suppressed. Yet the real run reaches `rmtree(legacy)`
in exactly this case (it passes `if to_copy or identical:` because
`identical` is non-empty), deleting the legacy tree.

`--dry-run`'s contract is to preview every change the real run would
make. For an identical-only legacy tree the deletion is the *only*
effect, and it is the one the preview hides.

## Why it matters

Reachability: a user who has already migrated once, or whose legacy
`deck/` was copied into `.game-of-cards/deck/` by hand, ends up with
a legacy tree that is byte-identical to canonical. Running
`goc migrate --dry-run` to check "is it safe to clean up the old
tree?" prints only:

```
Cards already in canonical tree (identical, will skip): 1
Dry run — no changes made.
```

— giving no hint that the actual `goc migrate` will `rmtree` the
legacy `deck/`. The preview understates a destructive action, which
is precisely the failure mode `--dry-run` exists to prevent.

This is distinct from
[goc-migrate-silently-destroys-card-files-other-than-readme-and-log](../goc-migrate-silently-destroys-card-files-other-than-readme-and-log/)
(that card is about the copy loop skipping non-README/log files
inside identical dirs); this card is about the dry-run *preview* not
matching the real run's deletion.

## Fix

Widen the dry-run guard at `engine.py:5080` so it fires whenever the
real run would reach `rmtree(legacy)` — i.e. include the `identical`
case:

```python
    if dry_run:
        if to_copy or identical or not legacy_dirs:
            print(f"Would remove legacy tree: {legacy}")
        print("Dry run — no changes made.")
        return
```

One-line, single-site change plus a regression test for the
identical-only case.

## Empirical evidence

See `reproduce.py`. Run with `uv run python
deck/migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees/reproduce.py`.
