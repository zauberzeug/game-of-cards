## 2026-05-29T23:23:09Z — Closure

- **What changed**: `goc/templates/hooks/deck_session_start.py:113-148` `_is_impeded` and `openclaw-plugin/index.ts:162-184` `isImpeded` — both now mirror the engine's `until_unparseable` backstop: when `waiting_until` is present-but-unparseable and `waiting_on` is empty, return True (impede) instead of falling through to `until_future` (False).
- **Verification**: `reproduce.py` exits 0 (engine `waiting_impedes` and hook `_is_impeded` both return True for `waiting_until: 2026-99-99` with no `waiting_on`); 239/239 regression tests pass; Node `--experimental-strip-types --test` matrix (8 cells) passes against the extracted TS source.
- **Audit**: PASS — no rubric configured; mechanical fix that aligns the two hook helpers with the documented engine `until_unparseable` backstop (`goc/engine.py:1778-1797`).
- **Project impact**: n/a
- **Tests**: 239 passed / 0 failed / 0 xfailed; `tests/test_openclaw_session_start_hook.py` added (Node-runner harness for the TS port); `tests/test_session_start_hook.py::test_is_impeded_true_for_bare_deferral_with_malformed_waiting_until` added.
- **Bundled with**: n/a

## Closure verification (2026-05-29T23:23:26Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
