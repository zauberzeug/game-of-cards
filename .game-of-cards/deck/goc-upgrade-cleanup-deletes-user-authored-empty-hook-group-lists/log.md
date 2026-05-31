## 2026-05-30T22:32:04Z — Closure

- **What changed**: `goc/install.py:749` — the per-group emptiness gate
  now preserves groups whose `hooks` list was already empty before the
  filter ran (`if new_hooks or not group_hooks`), mirroring the
  event-level `preexisting_empty` guard one layer up.
- **Verification**: `reproduce.py` exits 0 after fix; 2 new regression
  tests in `tests/test_install.py` exercise the placeholder-group case
  alongside a GoC-managed group and the lone-placeholder case.
- **Audit**: PASS — no principle touched, mechanical fix (parallel to
  the just-closed event-level sibling
  `goc-upgrade-cleanup-deletes-user-authored-empty-hook-event-lists`;
  same "preserve user-authored placeholders" pattern).
- **Project impact**: n/a
- **Tests**: 336 passed / 0 failed / 0 xfailed
- **Bundled with**: none

## Closure verification (2026-05-30T22:32:14Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
