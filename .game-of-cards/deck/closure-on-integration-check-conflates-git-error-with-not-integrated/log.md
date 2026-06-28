## 2026-06-24T01:35:00Z — Closure

- **What changed**: `goc/engine.py:4190` — `_enforce_closure_on_integration_or_exit` now blocks closure only on `git merge-base --is-ancestor` exit 1 (true non-ancestor); any other non-zero exit (e.g. 128, a git error) warns and skips, mirroring the sibling fetch-failure branch instead of misdiagnosing it as un-integrated work.
- **Verification**: reproduce.py — exit 0 → allow, exit 1 → block(2), exit 128 → warn&skip; all PASS. `tests/test_closure_on_integration_git_error.py` 3/3 ok. Full suite 554 passed after plugin-mirror re-sync.
- **Audit**: PASS — no principle touched, mechanical fix (exit-code disambiguation; fails open on git error, consistent with the existing fetch-failure posture in the same function).
- **Project impact**: n/a
- **Tests**: 554 passed / 0 failed / 0 xfailed
- **Bundled with**: (none)

## Closure verification (2026-06-24T01:31:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-06-24 — Closure' present
