# Log

## 2026-07-07 — reproduced, fixed, closed

Pulled off the queue by an autonomous run. `reproduce.py` landed and
confirmed the hypothesis on unfixed code: in a temp dir carrying only
`.game-of-cards/deck/.goc-version`, `goc install --dry-run` exited 0 with
an 18-write plan while `goc install` exited 1 with `already installed`.

Fix: moved the `_find_installed_deck_dir` already-installed guard in
`goc/install.py::install()` ahead of both `_plan_writes` and the dry-run
short-circuit, so dry-run and real run refuse identically. Dropped the
`unverified` tag per the DoD. Regression test
`test_install_dry_run_reports_already_installed_refusal` added next to the
existing already-installed test; full suite (699 tests) green after
re-syncing the plugin mirrors via `scripts/sync_plugin_assets.py`.

## 2026-07-07T01:45:56Z — Closure

- **What changed**: goc/install.py:1535-1546 — moved the
  `_find_installed_deck_dir` already-installed guard ahead of
  `_plan_writes` and the dry-run short-circuit, so `goc install --dry-run`
  refuses identically to the real run on an installed repo.
- **Verification**: reproduce.py exit 1 → 0 across the fix; new regression
  test `test_install_dry_run_reports_already_installed_refusal` asserts
  exit 1 + `already installed` on stderr + no write plan.
- **Audit**: PASS — no rubric configured; mechanical fix (restores the
  dry-run/executor parity contract tracked by the meta card).
- **Project impact**: n/a
- **Tests**: 699 passed / 0 failed (full unittest discover, post
  plugin-mirror re-sync)
- **Bundled with**: none

## Closure verification (2026-07-07T01:46:17Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 2/2 ticked
- [x] log-md-closure-entry — '## 2026-07-07 — Closure' present
