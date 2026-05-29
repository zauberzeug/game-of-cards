## 2026-05-29T23:56:02Z — Closure

- **What changed**: `goc/templates/hooks/deck_session_start.py:_is_impeded` and `openclaw-plugin/index.ts:isImpeded` — gate on "any non-None / non-empty `waiting_on`" (matching `engine.waiting_impedes`'s `reason is not None` gate) instead of enum membership in `{external, resource, deferred}`. Dead `_IMPEDED_WAITING_ON` / `IMPEDED_WAITING_ON` constants removed.
- **Verification**: `reproduce.py` exits 0 (was exit 1); two new pinning tests added — `test_is_impeded_true_for_non_canonical_waiting_on` (Python) and the two new `isImpeded("externl", ...)` / `isImpeded("customer-call", "not-a-date", ...)` cells (TS) — pass. Full regression suite: 240 tests passed.
- **Audit**: PASS — no rubric configured; mechanical fix mirroring the engine's existing contract.
- **Project impact**: n/a
- **Tests**: 240 passed / 0 failed / 0 xfailed

## Closure verification (2026-05-29T23:56:16Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
