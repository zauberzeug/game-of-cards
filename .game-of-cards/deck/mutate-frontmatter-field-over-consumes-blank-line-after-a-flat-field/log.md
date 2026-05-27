## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/engine.py:328` — restructured the `mutate_frontmatter_field` continuation regex so the block tail is an optional group that only opens with an indented line directly after the header; the internal-blank clause `\n(?=\n*[ \t])` now absorbs a blank only when a further indented line follows.
- **Verification**: reproduce.py exits 1 (fixed) — CASE1 blank preserved, CASE2 stray indented line preserved, CONTROL block-field tail preserved.
- **Audit**: PASS — no rubric configured; mechanical regex fix, no principle touched.
- **Project impact**: n/a
- **Tests**: no pytest suite; `uv run goc validate` clean, `sync_plugin_assets.py --check` clean.
- **Bundled with**: none

## Closure verification (2026-05-27T01:23:56Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
