## 2026-05-29 — Coercion choice

Chose `[]` (treat malformed `tags:` as empty) over `[value]` (wrap a
single string into a single-element list), mirroring the sibling
fixes for `compute_values` and `find_half_edges`. Rationale: silently
wrapping a typo turns a bad shape into a valid-looking single-tag
card that would then mislead `--tag` filters AND quietly pass through
the render path without ever surfacing the typo. Returning `[]` keeps
the field invisible to filter/render while leaving `goc validate` as
the canonical reporter of the bad shape.

## 2026-05-29T06:00:00Z — Closure

- **What changed**: goc/engine.py:505 (`Card.tags` property) — guard non-list frontmatter value with `isinstance(..., list)` before returning, matching the sibling pattern in `compute_values` (engine.py:1836) and `find_half_edges` (engine.py:1297).
- **Verification**: reproduce.py exits 0; render of bare-string `tags='bug'` is `''` (was `'b,u,g'`); filter `--tag b` does NOT substring-match (was True).
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 188 passed / 0 failed / 0 xfailed (full `uv run python -m unittest discover -s tests`). Added 4 regression cases in `tests/test_non_list_advances_guard.py` under `TagsPropertyGuardTest` covering render, filter, other non-list types, and list pass-through.
- **Bundled with**: n/a

## Closure verification (2026-05-29T05:40:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
