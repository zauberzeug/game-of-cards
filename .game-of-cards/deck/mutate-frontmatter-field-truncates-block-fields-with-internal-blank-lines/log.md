## 2026-05-26T00:00:00Z — Closure

- **What changed**: `goc/engine.py` `mutate_frontmatter_field` — widened the
  continuation pattern from `(?:\n[ \t]+[^\n]*)*` to
  `(?:\n[ \t]+[^\n]*|\n(?=[ \t]|\n))*` so internal blank lines belonging to a
  block field are consumed (the bare-`\n` alternative is gated by a lookahead
  so the match still stops at the next top-level `key:` line instead of
  swallowing the rest of the frontmatter).
- **Verification**: `reproduce.py` exits 0 (was exit 1, with `status` lost and
  `- [ ] b` orphaned). Flat-field mutation paths (`status`, `worker`,
  `closed_at`) and trailing/absent-field append confirmed unchanged.
- **Audit**: PASS — no principle touched, mechanical fix (regex anchoring).
- **Project impact**: n/a
- **Tests**: no pytest suite; `goc validate` clean.

## Closure verification (2026-05-26T21:29:02Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-26 — Closure' present
