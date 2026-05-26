## 2026-05-26T22:01:51Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:173` — dropped the trailing `.rstrip()` in `_parse_block_scalar` so block-scalar content lines keep trailing whitespace; only leading block indentation is stripped (`raw[block_indent:]`).
- **Verification**: reproduce.py exits 0; round-trip preserves trailing whitespace on first AND later content lines of a multi-line block scalar.
- **Audit**: PASS — no principle touched, mechanical fix (emit->parse serialization symmetry for block scalars; same round-trip-closure family as the closed inline-scalar quoting cards).
- **Project impact**: n/a
- **Tests**: `uv run goc validate` green; existing block-scalar regression (keep-chomping) reproduce passes; plugin mirror sync --check clean.

## Closure verification (2026-05-26T22:02:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
