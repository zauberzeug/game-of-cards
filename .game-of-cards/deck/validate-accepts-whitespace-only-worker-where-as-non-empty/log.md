## 2026-05-30T13:14:38Z — Closure

- **What changed**: `goc/engine.py:1269` — extended the `where` sub-key validator to reject whitespace-only strings, mirroring the existing `who` rule.
- **Verification**: `reproduce.py` flips from exit 0 → exit 1-with-expected-error; 5/5 worker-whitespace tests pass; 289/289 full regression suite passes.
- **Audit**: PASS — no rubric configured; mechanical sibling-fix bringing the `where` branch into symmetry with the `who` and bare-string branches already strip-checked by [validate-accepts-whitespace-only-worker-as-non-empty](../validate-accepts-whitespace-only-worker-as-non-empty/).
- **Project impact**: n/a
- **Tests**: 289 passed / 0 failed / 0 xfailed
- **Bundled with**: (single closure)

## Closure verification (2026-05-30T13:14:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
