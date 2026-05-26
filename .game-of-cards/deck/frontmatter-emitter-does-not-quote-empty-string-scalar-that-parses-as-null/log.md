## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `_parser_coerces_scalar` — lead the disjunction with `s == ""` so the emitter quote-trigger consults the parser's empty-string (`if not text`) coercion branch; `_yaml_inline("")` now emits `""`.
- **Verification**: reproduce.py exits 0 (`'' -> ''` round-trip preserved; `_parser_coerces_scalar('')` now True). Both sibling reproducers (integer/null/bool, indicator/whitespace) still PASS. `uv run goc validate` exit 0 after plugin-mirror sync.
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric serialization; the guard now mirrors all parser coercion branches).
- **Decision (PROCESS DoD)**: fix lands in `_parser_coerces_scalar`, not a standalone guard — keeps the single quote-trigger authority intact. This is the 3rd instance of the emitter-quote-class family; a 4th warrants the round-trip-by-construction meta-fix (emit, re-parse, quote iff differs).
- **Project impact**: n/a
- **Tests**: no pytest suite; reproduce.py + 2 sibling reproducers passed, goc validate clean.

## Closure verification (2026-05-26T21:48:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
