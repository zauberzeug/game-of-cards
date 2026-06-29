# Log

## 2026-06-29 — closed (done)

Fixed the caller-side gap: `upgrade()`'s same-version "nothing to do"
short-circuit returned before `_append_precommit_hook` ran, so a stale
legacy `files: ^deck/.*$` pre-commit glob was never migrated on a
re-upgrade at the current version.

- Added `_precommit_refresh_pending(target)` to `goc/install.py` — a
  pure (no-write) check that is true only when a real git repo has a
  GoC-managed `goc-validate` stanza that `_refresh_goc_validate_block`
  would change. Wired a `pending_precommit_refresh` signal into the
  short-circuit guard, mirroring the existing `pending_cleanup` /
  `pending_briefing_migration` carve-outs.
- The pristine-current no-op path is preserved: when the stanza is
  already up to date the flag is false and `goc upgrade` still prints
  "already at goc X — nothing to do."
- TDD: `reproduce.py` drives the real `upgrade()` flow at
  `__version__` with a legacy glob — FAIL (glob stays stale) before
  the fix, PASS (migrated to `.game-of-cards/deck`) after.
- Regression test `tests/test_upgrade_precommit_refresh_at_same_version.py`
  (migrate / no-op-preserved / pure-check). Full suite (641 tests) and
  `goc validate` green; plugin mirrors re-synced
  (claude/codex/openclaw `goc/install.py`).

Follow-up to the closed `goc-upgrade-leaves-stale-pre-commit-validate-pattern`,
which fixed the short-circuit *inside* `_append_precommit_hook` but
whose `reproduce.py` never traversed `upgrade()`'s own short-circuit.
