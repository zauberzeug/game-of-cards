## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/install.py:169` — `_strip_goc_block` now replaces the marker block with `\n\n` (not `\n`); the trailing `.strip()` keeps block-at-top / block-at-bottom / block-only edges clean.
- **Verification**: reproduce.py exits 0 — `Intro paragraph.\n\n## My Section\n` preserved. Edge cases checked: block-only and header+block still delete the file; block-at-top/bottom collapse to single trailing newline.
- **Audit**: PASS — no principle touched, mechanical fix (marker-bounded merge round-trip).
- **Project impact**: n/a
- **Tests**: goc validate clean; plugin mirrors re-synced (3 files).

## Closure verification (2026-05-27T07:48:15Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 2/2 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
