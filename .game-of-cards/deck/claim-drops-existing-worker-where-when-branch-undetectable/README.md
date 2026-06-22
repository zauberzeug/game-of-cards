---
title: claim-drops-existing-worker-where-when-branch-undetectable
summary: Claiming a card drops a stored worker.where when the current git branch is undetectable (detached HEAD / fresh checkout), instead of preserving it.
status: done
stage: null
contribution: medium
created: "2026-06-22T02:04:44Z"
closed_at: "2026-06-22T02:09:27Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TEST: a regression test in `tests/` claims a card carrying `worker: {who: <name>, where: <branch>}` with no `--worker-where` flag while the tree has no detectable branch (detached HEAD or `git rev-parse --abbrev-ref HEAD` → `HEAD`/empty), and asserts the existing `where` survives rather than being dropped.
  - [x] FIX: `_auto_populate_worker` falls back to the existing `worker.where` when no `--worker-where` flag is given and no usable branch is detected, instead of writing `where = None` (which collapses the worker to a bare `who` string).
  - [x] REGRESSION: existing `tests/test_auto_populate_worker_empty_who.py` still passes (empty-`who` cards stay untouched; a detectable branch is still recorded/updated).
worker: {who: "claude[bot]", where: main}
---

# claim-drops-existing-worker-where-when-branch-undetectable

## What's wrong

`_auto_populate_worker` (`goc/engine.py:4541-4588`) stamps the `worker`
field when a card is claimed via `goc status <title> active`. The `who`
sub-field is resolved with the precedence **flag → existing → git
config**:

```python
    if worker_who is not None:
        who = worker_who
    elif "who" in existing_dict:          # existing value preserved
        who = existing_dict["who"]
    else:
        r = subprocess.run(["git", "config", "user.name"], ...)
```

The `where` sub-field, however, never consults the existing value:

```python
    if worker_where is not None:
        where: str | None = worker_where
    else:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)
        where = r.stdout.strip() if r.returncode == 0 else None
        if where in ("", "HEAD"):
            where = None
```

When no `--worker-where` flag is passed **and** the current git state
yields no usable branch — a detached HEAD or a fresh checkout where
`git rev-parse --abbrev-ref HEAD` prints `HEAD` (or empty) — `where`
becomes `None`. Downstream, with `who` truthy and `where` falsy, the
function rebuilds the field as a bare string:

```python
    if where:
        worker_yaml = f"{{who: {who_yaml}, where: {where_yaml}}}"
    else:
        worker_yaml = who_yaml          # <-- existing `where` silently dropped
```

So a card that arrived as `worker: {who: alice, where: feature/foo}` is
rewritten to `worker: alice` — the persisted branch context is
destroyed, replaced with nothing.

## Why it matters

AGENTS.md documents `worker.where` as durable, contract-bearing state:
the mapping form `worker: {who: rodja, where: feature/foo}` records
branch context, and "the field persists after close as a historical
record." Dropping it on a routine claim is silent data loss.

Reachability is concrete and routine, not theoretical:

- A filer hand-authors `worker: {who: rodja, where: feature/foo}` as a
  directive (AGENTS.md sanctions this exact form).
- An autonomous runner on a **detached-HEAD checkout** (common in CI
  and container runs — GitHub Actions checks out a detached HEAD by
  default) claims the card with `goc status <title> active` and no
  `--worker-where`.
- `git rev-parse --abbrev-ref HEAD` returns `HEAD`, `where` collapses to
  `None`, and the stored `feature/foo` is gone.

Note the scope: when a branch **is** detectable, updating `where` to the
current branch is the documented intent ("preserve [who] and only
add/update `where`"). This card does **not** change that. It fixes only
the drop-to-nothing case — losing existing data when there is no
replacement value to write.

## The fix

In `_auto_populate_worker`, after git branch detection yields `None`,
fall back to the existing `where`:

```python
    if worker_where is not None:
        where: str | None = worker_where
    else:
        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)
        where = r.stdout.strip() if r.returncode == 0 else None
        if where in ("", "HEAD"):
            where = None
        if where is None:
            # No detectable branch (detached HEAD / fresh checkout):
            # preserve any stored branch context rather than dropping it.
            where = existing_dict.get("where")
```

Single-site fix plus one regression test. See `reproduce.py` for the
empirical demonstration.
