## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py:336` — `mutate_frontmatter_field` now passes a callable (`lambda _: f"{field_name}: {new_value}"`) to `pattern.sub` so `new_value` is no longer interpreted as a regex replacement template; backslash-bearing values land verbatim.
- **Verification**: reproduce.py exits 0 (both Windows-path and regex-backreference cases round-trip unchanged); was exit 1 before the fix.
- **Audit**: PASS — no principle touched, mechanical fix (field-symmetric serialization).
- **Project impact**: n/a
- **Tests**: 159 passed / 0 failed / 0 xfailed (4 subtests passed); plugin mirror parity + goc validate clean.
- **Bundled with**: (none)

## Closure verification (2026-05-27T00:04:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
