## 2026-06-20T05:40:00Z — Closure

- **What changed**: `goc/engine.py:3075` — `quality-pass --limit` now uses `type=_non_negative_int` (was `type=int`), so a negative value is rejected at the argparse layer instead of silently mis-slicing `cards[:limit]`. Mirrors the existing `--max-rows` guard.
- **Verification**: `reproduce.py` exits 0 (negative `--limit` rejected; `0` and `3` still parse). New `tests/test_quality_pass_limit.py` (3 tests) passes.
- **Audit**: PASS — no principle touched, mechanical fix (bounds check on a count-style CLI flag; precedent set by closed card `negative-board-row-limit-hides-cards`).
- **Project impact**: n/a
- **Tests**: 472 passed / 0 failed (full suite); plugin mirrors re-synced via `scripts/sync_plugin_assets.py`.
- **Bundled with**: (none)

## Closure verification (2026-06-20T05:25:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-20 — Closure' present
