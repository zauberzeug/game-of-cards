## 2026-05-26T22:06:40Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py` `_parse_block_scalar` — raise `ParseError` when a non-blank content line is indented strictly less than the established `block_indent` (but more than the declaration), instead of slicing `raw[block_indent:]` and eating leading characters.
- **Verification**: reproduce.py exits 0 (raises `ParseError: line 3: ... ambiguous indentation`); against the unfixed parser it exited 1 with `k == 'deep line\nallow line\n'` (the `sh` of `shallow` eaten).
- **Audit**: PASS — no project rubric configured; mechanical correctness fix (parser rejects malformed indentation rather than silently corrupting).
- **Project impact**: n/a
- **Tests**: `uv run goc validate` clean (0 ERROR/FAIL); sibling block-scalar round-trip reproduce.py still exits 0; plugin mirrors re-synced.
- **Bundled with**: (none)

## Closure verification (2026-05-26T22:06:50Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
