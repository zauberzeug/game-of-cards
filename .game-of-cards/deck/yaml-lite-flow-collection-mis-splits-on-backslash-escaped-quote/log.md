## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py` — `_split_flow` and the structurally-identical `_split_key` now track a backslash escape inside double-quoted strings (skip the char after a `\`), so an emitter-produced `\"` is not seen as a delimiting quote and the structural comma after it is not swallowed.
- **Verification**: `reproduce.py` exits 0 — case 1 (`worker` mapping with `who: 'a"'`) round-trips both keys exactly; case 2 (flow sequence `["a\"", "b"]`) splits into two elements.
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric serialization: the parser now reads back what its own emitter wrote).
- **Project impact**: n/a
- **Tests**: 165 passed / 0 failed (added `EscapedQuoteFlowSplitTest` to `tests/test_yaml_lite.py` covering flow-mapping, flow-sequence, block-key, and engine emit→parse round-trip).
- **Bundled with**: n/a

## Closure verification (2026-05-27T11:31:29Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
