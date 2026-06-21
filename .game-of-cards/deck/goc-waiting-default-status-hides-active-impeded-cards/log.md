## 2026-06-21T12:30:00Z — Closure

- **What changed**: `goc/engine.py` `_cmd_default` — default status filter now extends to `all` when `--waiting` is set and `--status` is not explicit (mirroring the `--closed-since` precedent), so active impeded cards are no longer dropped before the `--waiting` filter runs.
- **Verification**: reproduce.py exits 0 (both `open-impeded` and `active-impeded` surface in `goc --waiting`); new `tests/test_waiting_filter_status_scope.py` (2 tests) passes; explicit `--status open` still narrows to open.
- **Audit**: PASS — no principle touched, mechanical fix (closing a CLI-flag asymmetry against the documented three-axis stuck model).
- **Project impact**: n/a
- **Tests**: 499 passed / 0 failed / 0 xfailed (full suite); plugin mirrors re-synced for the engine edit.
- **Bundled with**: n/a

## Closure verification (2026-06-21T12:23:28Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present
