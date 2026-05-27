## 2026-05-27T10:01:49Z — Closure

- **What changed**: `goc/engine.py` — added `_display_width` / `_display_ljust`
  (stdlib `unicodedata.east_asian_width`) and used them in `render_board` for
  column-width computation, header padding, and cell padding instead of
  `len()` / `str.ljust()`. Plugin mirrors re-synced.
- **Verification**: `reproduce.py` exits 0 — header/unmarked/marked rows' first
  `|` separator all land at display column 21 (was 21/21/22 before the fix).
- **Audit**: PASS — invokes the no-third-party-runtime-deps principle
  (`drop-third-party-runtime-dependencies-from-goc`): resolved the
  vendor-table-vs-`wcwidth` decision by using stdlib `unicodedata`, adding no
  dependency.
- **Project impact**: `goc --board` grid no longer skews on rows bearing the
  `⏳` impediment marker.
- **Tests**: no pytest suite; `goc validate` clean (exit 0), reproduce.py exit 0.
- **Bundled with**: n/a

## Closure verification (2026-05-27T10:02:00Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
