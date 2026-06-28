## 2026-05-30T13:28:36Z — Closure

- **What changed**: `goc/engine.py:1259` — added a `summary` content check
  to `validate_card` mirroring the existing worker block; rejects
  `summary: ""` and `summary: "   "` with
  `<title>: summary: must not be empty or whitespace-only`. Removed the
  `"summary": ""` default from `_cmd_new` at `goc/engine.py:4198` so
  freshly-scaffolded cards omit the optional field rather than tripping
  the new check immediately at creation.
- **Verification**: `tests/test_validate_summary_whitespace.py` (3 new
  tests, all pass); `reproduce.py` now exits 1 with
  `ERROR: ws-summary: summary: must not be empty or whitespace-only`;
  full regression suite — 292 passed / 0 failed.
- **Audit**: PASS — no principle touched, mechanical fix (closes the
  validate/quality-pass contract drift for the `summary` field, same
  shape as the worker fix family).
- **Project impact**: n/a
- **Tests**: 292 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## Closure verification (2026-05-30T13:28:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
