## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/_vendor/yaml_lite.py` — `_parse_block_scalar` now takes a three-way `chomp` ("clip"/"strip"/"keep") instead of a boolean `strip`; `_resolve_value` maps `|`→clip, `|-`→strip, `|+`→keep.
- **Symptom was inverted**: inspection guessed `|+` collapsed onto `|`; the reproduce.py showed `|+` (keep) was already correct, while **both `|` (clip) and `|-` (strip) wrongly retained trailing blank lines**. Fix is the same — real three-way chomp.
- **Verification**: reproduce.py exits 0 — clip `'a\n\n\n'`→`'a\n'`, strip `'a\n\n'`→`'a'`, keep `'a\n\n\n'` (unchanged); keep now distinct from clip. No goc round-trip change: `_emit_block_field` rstrips trailing newlines, so goc never emits trailing blanks to chomp.
- **Audit**: PASS — no principle touched, mechanical fix (YAML 1.1/1.2 chomp-indicator conformance).
- **Project impact**: n/a
- **Tests**: 152 passed / 0 failed / 0 xfailed; `goc validate` clean; plugin mirrors synced (3 files).

## Closure verification (2026-05-26T21:39:41Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
