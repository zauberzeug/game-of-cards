## 2026-06-18T05:20:00Z — Closure

- **What changed**: `goc/engine.py:190` — `_YAML_BLOCK_HEADER_RE` folded branch gains `\d*` (`>[-+]?` → `>\d*[-+]?`) so the emitter quotes folded-with-explicit-indent scalars (`>2`, `>3`, `>10`, `>2-`, `>2+`) that the yaml-lite parser recognizes as folded headers and rejects. Comment updated to document the coupling to `_FOLDED_INDICATOR_RE`.
- **Verification**: reproduce.py exits 0 — all 5 folded values now round-trip (previously crashed with FrontmatterError); pipe controls still OK. New regression test `tests.test_yaml_lite.BlockScalarIndicatorRoundTripTest.test_single_line_block_header_shaped_scalar_round_trips` covers pipe + folded families.
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric serialization: emitter recognizer mirrors parser recognizer).
- **Project impact**: n/a
- **Tests**: 456 passed / 0 failed (plugin-mirror parity restored after sync); plus the new round-trip test.
- **Bundled with**: n/a

## Closure verification (2026-06-18T05:05:20Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-18 — Closure' present
