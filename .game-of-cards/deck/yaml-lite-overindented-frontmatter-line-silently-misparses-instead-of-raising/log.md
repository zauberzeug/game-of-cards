## 2026-06-22T15:30:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:_parse_block_mapping` — added a `curr > indent` branch that raises `ParseError` instead of falling through to `_split_key`, so an over-indented mapping key (Case 1) and an over-indented bare-scalar continuation (Case 2) fail loud rather than being silently flattened/truncated.
- **Verification**: reproduce.py exits 0 (both cases raise ParseError); full regression suite 518 passed / 0 failed (4 new tests in `OverIndentedMappingRejectionTest`).
- **Audit**: PASS — no principle touched, mechanical fix (fail-loud parser guard mirroring the existing tab guard in `_peek` and the ambiguous-indent guard in `_parse_block_scalar`).
- **Project impact**: n/a
- **Tests**: 518 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-06-22T15:18:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-22 — Closure' present
