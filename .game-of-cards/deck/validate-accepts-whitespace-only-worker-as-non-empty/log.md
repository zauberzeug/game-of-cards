## 2026-05-30T13:07:06Z — Closure

- **What changed**: `goc/engine.py:1259-1268` — validator now strips before the emptiness check, so whitespace-only `worker` strings and whitespace-only `worker.who` mapping values are rejected.
- **Verification**: `reproduce.py` exits 0 (validator rejects both forms with non-zero exit, emitting `ws-bare: worker: must not be empty or whitespace-only` and `ws-mapping: worker: 'who' must be a non-empty, non-whitespace string`). New regression test `tests/test_validate_worker_whitespace.py` covers bare-string, mapping-who, mapping-who-with-where, and the valid-string negative.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a.
- **Tests**: 288 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-05-30T13:07:25Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
