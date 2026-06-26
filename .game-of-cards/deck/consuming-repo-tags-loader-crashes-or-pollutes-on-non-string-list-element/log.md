## 2026-06-26T01:50:00Z — Closure

- **What changed**: `goc/engine.py:620-627` — `_load_consuming_repo_tags()` now filters list elements to `str` (`out.update(t for t in value if isinstance(t, str))`) instead of passing the raw list to `set.update`. Drops unhashable elements (no `TypeError` crash) and hashable non-strings (no tag-set pollution). Plugin mirrors re-synced.
- **Verification**: `reproduce.py` exits 0 — both `[nested, list]` and `123/true` cases now return `{'good-tag'}`. Two new regression tests in `tests/test_consuming_repo_tags_loader.py`.
- **Audit**: PASS — no principle touched, mechanical fix (element type-guard mirroring the engine's existing non-string-element guard family).
- **Project impact**: n/a
- **Tests**: 602 passed / 0 failed (full suite); `goc validate` clean.
- **Bundled with**: (none)

Surfaced by an audit-deck pass when the ready queue was empty, then
fixed through in the same session (single-site, gate-free, near loaded
context). Distinct from the closed
[canonical-tags-loader-iterates-bare-string-scalar-character-by-character](../canonical-tags-loader-iterates-bare-string-scalar-character-by-character/),
which guarded the container shape but not the element types.

## Closure verification (2026-06-26T01:52:46Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-26 — Closure' present
