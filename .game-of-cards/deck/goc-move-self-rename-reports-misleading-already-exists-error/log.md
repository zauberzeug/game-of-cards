## 2026-06-24T14:00:00Z — Closure

- **What changed**: `goc/engine.py:5346` — added an early `old_title == new_title` identity guard in `_cmd_move`, before the src/dst existence checks, so a self-rename names the real condition instead of tripping the `dst.exists()` collision branch.
- **Verification**: `reproduce.py` now exits 0; stderr is `cannot move a card to itself (...)` and no longer contains "already exists".
- **Audit**: PASS — no principle touched, mechanical fix (matches the existing identity-guard convention in `_cmd_advance` / `_cmd_status --by`).
- **Project impact**: n/a
- **Tests**: 4 passed (new `tests/test_move_self_rename_guard.py` + existing `tests/test_move_rewrites_untracked_card.py`) / 0 failed.
- **Bundled with**: none

## Closure verification (2026-06-24T13:40:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present
