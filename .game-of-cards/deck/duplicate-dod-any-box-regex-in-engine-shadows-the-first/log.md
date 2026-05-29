## 2026-05-29T17:29:32Z — Closure

- **What changed**: `goc/engine.py:480` — deleted the duplicate `DOD_ANY_BOX = re.compile(...)` rebind, leaving only the canonical definition at line 464 with its explanatory comment.
- **Verification**: 235 tests pass, including the new `tests/test_engine_module_singletons.py::test_dod_any_box_defined_once` which asserts exactly one `DOD_ANY_BOX = re.compile` line at module scope.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a.
- **Tests**: 235 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-05-29T17:29:40Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
