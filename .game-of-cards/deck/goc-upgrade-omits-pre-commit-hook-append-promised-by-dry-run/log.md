## 2026-06-17T04:42:40Z — Closure

- **What changed**: `goc/install.py` `upgrade()` — added the idempotent `_append_precommit_hook(target / ".pre-commit-config.yaml")` call so the real upgrade performs the pre-commit append its dry-run plan already advertised.
- **Verification**: reproduce.py exits 0 (was exit 1); 2 new regression tests in `tests/test_install.py` pass; full suite 453 passed; `goc validate` clean.
- **Audit**: PASS — no rubric configured; mechanical fix restoring dry-run/real-run parity (no project principle touched).
- **Project impact**: n/a
- **Tests**: 453 passed / 0 failed / 0 xfailed

## Closure verification (2026-06-17T04:42:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-06-17 — Closure' present
