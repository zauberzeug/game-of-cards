## 2026-05-26T23:10:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py:163-172` — the `rstripped == ""`
  short-circuit in `_parse_block_scalar` now branches on `block_indent`: it
  still appends `""` for structural blanks before the block indent is fixed,
  but once `block_indent` is known it slices `raw[block_indent:]` so a
  whitespace-only content line keeps its interior spaces. The existing
  trailing-blank chomp (`chunks[end-1] == ""`) is untouched, so genuinely-empty
  trailing lines still chomp while whitespace-only lines round-trip.
- **Verification**: `reproduce.py` exits 0; `'first line\n   \nthird line'`
  now round-trips (was `'first line\n\nthird line'`). Added 4 regression tests
  to `tests/test_yaml_lite.py` (interior ws line, sub-indent blank, trailing
  genuine-blank chomp, trailing ws line preserved).
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric
  emit->parse round-trip restoration in the vendored YAML subset).
- **Project impact**: n/a
- **Tests**: 156 passed / 0 failed / 0 xfailed (full suite); yaml_lite 29 passed
- **Bundled with**: none

Note: a block scalar whose lines are *all* whitespace-only (no non-empty line
to fix the indentation level) still resolves to `""`, matching YAML's
auto-indent-detection semantics. The realistic case (interior/trailing
whitespace mixed with content) round-trips; the single-line value `"   "` goes
through the inline-quoted emit path and round-trips there.

## Closure verification (2026-05-26T22:47:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
