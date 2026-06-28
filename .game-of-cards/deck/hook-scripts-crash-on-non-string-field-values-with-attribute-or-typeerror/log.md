## 2026-05-31T04:30:00Z — Closure

- **What changed**: `goc/templates/hooks/deck_prompt_router.py:79` + `goc/templates/hooks/pattern_generalization_check.py:201` — added per-field `isinstance(..., str)` guards mirroring the predecessor's dict-level discipline one layer deeper. Plugin mirrors regenerated via `sync_plugin_assets.py`.
- **Verification**: `reproduce.py` now exits 0; both hooks return 0 silently on `{"prompt": 123}` and `{"transcript_path": 123}`. `uv run goc validate` OK; `uv run python -m unittest discover -s tests` → 348 passed.
- **Audit**: PASS — no principle touched, mechanical fix (mirrors the contract restored by the closed predecessor [`hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror`](../hook-scripts-crash-on-non-dict-stdin-json-with-attributeerror/)).
- **Project impact**: n/a
- **Tests**: 348 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## Closure verification (2026-05-31T04:28:34Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-31 — Closure' present
