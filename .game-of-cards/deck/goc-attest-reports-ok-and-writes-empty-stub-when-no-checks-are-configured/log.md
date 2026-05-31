## 2026-05-31T04:01:07Z — Closure

- **What changed**: `goc/engine.py:4115` — `_cmd_attest` short-circuits with exit 2 and an "ERROR: no closure checks configured" stderr message when both `layer_2_project_dod` and `layer_3_goc_dod` are empty/unset; `log.md` is not touched.
- **Verification**: `reproduce.py` now exits 0 (post-fix verdict); new regression `tests/test_install.py::test_attest_refuses_when_both_layers_are_empty_and_leaves_log_untouched` asserts exit code 2, stderr message, and no `## Closure verification` header in log.md.
- **Audit**: PASS — no rubric configured; mechanical fix to align attest with the refuse-when-prerequisites-unmet posture used elsewhere in the engine.
- **Tests**: 348 passed / 0 failed / 0 xfailed.
- **Bundled with**: none.

## Closure verification (2026-05-31T04:01:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-31 — Closure' present
