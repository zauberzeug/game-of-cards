## 2026-06-22T15:00:00Z — Closure

- **What changed**: `goc/install.py:786-794` — guard `skills_src.iterdir()` with `skills_src.is_dir()` so an absent template skill tree (plugin payload shape) yields an empty GoC-owned set instead of raising `FileNotFoundError`.
- **Verification**: reproduce.py exits 0 post-fix (was exit 1 with FileNotFoundError); new regression test `test_strip_vendored_harness_survives_absent_template_skill_tree` verified to fail without the guard and pass with it.
- **Audit**: PASS — no principle touched, mechanical fix (defensive guard; conservative behavior preserves authored content when GoC-owned skill names cannot be derived).
- **Project impact**: n/a
- **Tests**: 514 passed / 0 failed / 0 xfailed.
- **Bundled with**: (none)

## Closure verification (2026-06-22T14:40:30Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-22 — Closure' present
