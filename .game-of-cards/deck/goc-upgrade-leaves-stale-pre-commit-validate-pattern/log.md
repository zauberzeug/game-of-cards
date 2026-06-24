## 2026-06-24T08:45:00Z — Closure

- **What changed**: `goc/install.py` `_append_precommit_hook` + new `_refresh_goc_validate_block` — upgrade now re-emits a stale GoC-managed `goc-validate` stanza in place instead of no-opping, migrating the legacy `files: ^deck/.*$` glob to `^\.game-of-cards/deck/.*$`.
- **Verification**: reproduce.py exit 0 (`CHANGED: True`, legacy glob gone, new path present); 3 new regression tests in `tests/test_install.py::RefreshStalePrecommitHookTest` (migrate / byte-identical-no-op / preserve-unrelated-hook) pass.
- **Audit**: PASS — no principle touched, mechanical fix (config-file repair; conservative guard preserves authored content).
- **Project impact**: n/a
- **Tests**: 566 passed / 0 failed; `goc validate` exit 0; plugin mirrors re-synced (claude/codex/openclaw goc/install.py).
- **Bundled with**: n/a

## Closure verification (2026-06-24T08:35:52Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present
