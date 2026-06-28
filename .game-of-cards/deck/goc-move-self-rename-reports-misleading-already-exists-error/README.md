---
title: goc-move-self-rename-reports-misleading-already-exists-error
status: done
stage: null
contribution: medium
created: "2026-06-24T13:37:56Z"
closed_at: "2026-06-24T13:40:29Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
summary: "`goc move <title> <title>` (old == new) resolves `src` and `dst` to the same directory, so the source-exists check passes and the destination-exists check then fires — because `dst` is `src` — aborting with a phantom `ERROR: <dst> already exists` collision instead of a clean no-op or a self-rename-specific message."
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (self-rename no longer reports a phantom collision)
  - [x] TDD: `goc move <X> <X>` errors with a self-rename message (exit 2) and the stderr does NOT contain "already exists"
  - [x] MECHANICAL: an early `old_title == new_title` guard is added in `_cmd_move` before the src/dst existence checks, matching the identity-guard convention of `_cmd_advance` / `_cmd_status --by`
---

# goc-move-self-rename-reports-misleading-already-exists-error

## Summary

`goc move <X> <X>` (old and new titles identical) aborts with
`ERROR: <deck>/<X> already exists`, as if the user were trying to
clobber a *different* card. There is no early identity guard, so the
no-op self-rename trips the `dst.exists()` collision check.

## Location

`goc/engine.py:5346-5353` (`_cmd_move`).

## What's broken

When `old_title == new_title`, `src` and `dst` resolve to the **same**
directory. The source-exists check passes (the card exists), then the
destination-exists check fires — because `dst` *is* `src` — and the
command aborts with a phantom-collision diagnosis:

```python
    src = DECK_DIR / old_title
    dst = DECK_DIR / new_title
    if not src.exists():
        print(f"ERROR: {src} does not exist", file=sys.stderr)
        sys.exit(2)
    if dst.exists():
        print(f"ERROR: {dst} already exists", file=sys.stderr)
        sys.exit(2)
```

The message blames a collision with an existing card, but the real
condition is "you asked to rename a card to itself." The sibling
mutation verbs all carry an explicit identity guard that names the
real condition — `_cmd_advance` (`engine.py:5205`):

```python
    if title == advancer:
        print("ERROR: cannot advance a card with itself", file=sys.stderr)
        sys.exit(2)
```

and `_cmd_status --by` (`engine.py:4717`):

```python
    if successor is not None and successor == title:
        print(f"ERROR: --by {successor!r} cannot equal the card being superseded", file=sys.stderr)
        sys.exit(2)
```

`_cmd_move` is the lone identity-input verb missing this guard.

## Empirical evidence

Before the fix (`reproduce.py` against a throwaway temp deck):

```
exit code : 2
stderr    : 'ERROR: .../deck/sample-card-for-self-rename already exists'
BUG: self-rename reported a phantom collision ('already exists') ...
```

After the fix:

```
exit code : 2
stderr    : "ERROR: cannot move a card to itself (old and new titles are both 'sample-card-for-self-rename')"
OK: self-rename no longer reports a phantom collision.
```

## Why it matters

`goc move` is the user-facing rename verb (wired through `cli.py`). A
fat-finger that repeats the slug, or a script that computes
`new == old`, gets a diagnosis pointing at the wrong problem ("a
different card already occupies that slug") and may send the user
hunting for a non-existent collision instead of noticing the typo.
The reachability path is direct: `cli.py` parses two positional
title args and hands them to `_cmd_move`; nothing upstream rejects
`old == new`, so the identical-title shape flows straight into the
collision branch.

## Fix (applied)

An early identity guard was added in `_cmd_move` (`engine.py:5346`),
immediately after the title-pattern validation and before the
`src`/`dst` existence checks, matching the house convention:

```python
    if old_title == new_title:
        print(f"ERROR: cannot move a card to itself (old and new titles are both {new_title!r})", file=sys.stderr)
        sys.exit(2)
```

It errors with exit 2 and a message that names the real condition; the
stderr no longer contains the misleading "already exists" string.
Covered by `tests/test_move_self_rename_guard.py`.
