## 2026-06-18T00:00:00Z — Closure

- **What changed**: `goc/install.py:863` — gate the `.pre-commit-config.yaml` append in `_plan_writes` on `(target / ".git").exists()`, mirroring the git-aware executor `_append_precommit_hook`. `_plan_upgrade_writes` inherits the fix (it consumes `_plan_writes`). Stale comment at the real-upgrade append site updated.
- **Verification**: reproduce.py exits 0 (was: DEFECT REPRODUCED); non-git dry-run plan size 19 → 18; git-repo plan unchanged.
- **Audit**: PASS — no principle touched, mechanical fix (plan/executor parity)
- **Project impact**: n/a
- **Tests**: 457 passed / 0 failed (plus new `test_dry_run_omits_pre_commit_append_in_non_git_dir`); `goc validate` OK; plugin mirrors re-synced and parity green.

## Closure verification (2026-06-18T05:13:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-18 — Closure' present
