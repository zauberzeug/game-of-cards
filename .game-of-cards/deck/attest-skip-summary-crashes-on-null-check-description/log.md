## 2026-06-22T02:29:39Z — Closure

- **What changed**: `goc/engine.py:4495` — the `_cmd_attest` skip branch now builds its summary with null-coalescing `(check.get('description') or '')[:60]`, so a closure check authored with `description: null` renders an empty parenthetical instead of crashing on `None[:60]`.
- **Verification**: `reproduce.py` exits 0 (was exit 1 with `TypeError: 'NoneType' object is not subscriptable`); new regression test `test_attest_skip_with_null_check_description_does_not_crash` fails on the pre-fix engine and passes after the fix.
- **Audit**: PASS — no principle touched, mechanical fix (null-safe slice).
- **Project impact**: n/a
- **Tests**: 507 passed / 0 failed; plugin-mirror parity green after `sync_plugin_assets.py`.
- **Bundled with**: (none)

## Closure verification (2026-06-22T02:29:58Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-22 — Closure' present
