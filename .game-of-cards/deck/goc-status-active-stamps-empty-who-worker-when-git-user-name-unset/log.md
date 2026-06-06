## 2026-06-06T05:05:00Z — Closure

- **What changed**: `goc/engine.py:4290` — `_auto_populate_worker` guard
  changed from `if not who and not where` to `if not who`, so a claim never
  stamps an invalid empty-`who` worker (dropped the now-dead `'""'` fallback).
- **Verification**: `reproduce.py` 0 → 1; `tests/test_auto_populate_worker_empty_who.py` passes.
- **Audit**: PASS — no rubric configured; mechanical fix (no project principle touched).
- **Project impact**: n/a
- **Tests**: 394 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## 2026-06-06 — filed + fixed (fix-through)

Surfaced during a `pull-card` queue-empty audit pass. Confirmed reachable
with `reproduce.py`: in a temp git repo on branch `main` with `user.name`
unset, `_auto_populate_worker` hand-built `worker: {who: "", where: main}`,
which `validate_card` then rejected.

**Fix (engine.py:4290):** replaced the both-empty guard
`if not who and not where: return text` with `if not who: return text`. A
worker mapping requires a non-empty `who`, and a `where`-only worker is
itself invalid per the schema — so when `who` is unknown there is no valid
worker to stamp, even if a branch is known. Skipping is forced, not a taste
call; the only alternatives (`{who: "", where: ...}` or `{where: ...}`) are
both rejected by `validate_card`. Also dropped the now-dead
`if who else '""'` fallback on the line below, since `who` is guaranteed
truthy past the guard. The status transition still succeeds; it just records
no worker when identity is undetermined — the same outcome a fully
unconfigured checkout already produced.

**Verification:** `reproduce.py` flips 0 → 1; new
`tests/test_auto_populate_worker_empty_who.py` (empty-who-leaves-unchanged +
explicit-who-still-stamps-branch positive control) passes; full suite 394
green; `uv run goc validate` clean; plugin mirrors re-synced via
`scripts/sync_plugin_assets.py`.

The sibling card
[worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/)
(the `_emit_worker` re-emit path) stays open and UNVERIFIED — a distinct
site this fix does not touch.

## Closure verification (2026-06-06T04:55:23Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-06 — Closure' present
