## 2026-05-27T00:00:00Z — Closure

- **What changed**: `goc/install.py:1089` — rewrite regex changed from `^[#\s]*skills_source\s*:.*$` to `^[ \t]*#?[ \t]*skills_source[ \t]*:.*$` so `[ \t]*` can no longer back-consume newlines / blank-line separators.
- **Verification**: reproduce.py exits 0 (both cases `preserved: True`); new `test_write_skills_source_preserves_blank_separators_and_comments` passes.
- **Audit**: PASS — no principle touched, mechanical fix (no project rubric configured).
- **Tests**: 73 passed / 0 failed (tests.test_install).

## Closure verification (2026-05-27T13:31:20Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-05-27 — Closure' present
