
## 2026-06-10T05:17:36Z — Closure

- **What changed**: `goc/engine.py` `_cmd_attest` — after the empty-config guard, refuse (exit 2, no log.md mutation) when the set of configured check names is a subset of `--skip`, mirroring the empty-config "proves nothing" guard. Docstring documents the all-skipped contract.
- **Verification**: reproduce.py flips exit 0→1 (defect gone); all-skipped `goc attest` now exits 2 with "every configured closure check was skipped" and writes no Closure verification block; partial-skip path still attests OK.
- **Audit**: PASS — no principle touched, mechanical fix (closes an integrity hole symmetric with the existing empty-config guard).
- **Project impact**: n/a
- **Tests**: 419 passed / 0 failed (full suite); 2 new regression tests in tests/test_install.py (all-skip refusal + partial-skip still runs).

## Closure verification (2026-06-10T05:17:39Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-10 — Closure' present
