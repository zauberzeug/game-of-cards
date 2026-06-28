## 2026-06-03T05:05:00Z — Closure

- **What changed**: `goc/engine.py` `_cmd_migrate` dry-run preview — widened the guard from `to_copy or not legacy_dirs` to `to_copy or identical or not legacy_dirs` so `--dry-run` announces the legacy-tree removal in every case the real run reaches `rmtree(legacy)`, including the identical-only case.
- **Verification**: reproduce.py now exits 0 (dry-run prints `Would remove legacy tree`, legacy tree intact); new regression test `test_migrate_dry_run_announces_removal_for_identical_only_tree` passes.
- **Audit**: PASS — no principle touched, mechanical fix (dry-run preview must mirror the real run's effects; no project-principle binding).
- **Project impact**: n/a
- **Tests**: 355 passed / 0 failed (full `unittest discover -s tests`); `goc validate` clean.
- **Bundled with**: (none)

## Closure verification (2026-06-03T04:55:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-03 — Closure' present
