## 2026-06-07T05:10:00Z — Closure

- **What changed**: `goc/install.py:1356-1369` — `_write_skills_source` now prefers the active (non-commented) `skills_source:` line and only un-comments a commented example when no active line exists, instead of a single `#?`-optional pattern + `count=1` that rewrote whichever line came first in document order.
- **Verification**: reproduce.py exits 0; the commented-doc-example-above-active-key case now yields exactly one active key (`# skills_source: auto\n\nskills_source: plugin\n`) instead of two conflicting keys.
- **Audit**: PASS — no principle touched, mechanical fix (line-oriented config rewrite correctness).
- **Project impact**: n/a
- **Tests**: 399 passed / 0 failed (full suite); plugin mirror parity green after `scripts/sync_plugin_assets.py` regenerated the 3 install.py mirrors.
- **Bundled with**: none

## Closure verification (2026-06-07T05:01:35Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-07 — Closure' present
