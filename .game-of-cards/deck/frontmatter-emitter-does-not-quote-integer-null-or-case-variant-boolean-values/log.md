## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` — removed `_YAML_RESERVED`; added `_parser_coerces_scalar()` that references the vendored parser's own `_NULL_SET`/`_TRUE_SET`/`_FALSE_SET`/`_INT_RE`; the `_yaml_inline` quote-trigger now calls it, so int-/null-/case-variant-bool-looking string scalars are quoted and survive the emit->parse round-trip.
- **Verification**: reproduce.py exits 0 — 12/12 string values round-trip unchanged (was 11/12 LOSS). Genuine int/float/bool/None still emit bare; date strings and prose unchanged.
- **Audit**: PASS — no project rubric configured; field-symmetric serialization fix that closes the emit->parse round-trip on the core persistence path. Truth-set duplication eliminated (emitter now derives recognition from the parser by reference).
- **Project impact**: n/a
- **Tests**: no pytest suite; `uv run goc validate` passes (exit 0) after plugin-mirror sync.
- **Bundled with**: none

## Closure verification (2026-05-26T21:02:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
