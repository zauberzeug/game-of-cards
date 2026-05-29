## 2026-05-29T17:30:00Z — Closure

- **What changed**: `openclaw-plugin/index.ts:46-63` — added `"wait"` and `"repair-edges"` to `GOC_VERBS` literal-union in the engine-declared order (between `new`/`advance` and between `unadvance`/`move`). Regenerated `openclaw-plugin/dist/index.js` via `npm run build` so the compiled `GOC_VERBS` shipped to OpenClaw consumers matches the TS source.
- **Drift guard**: `tests/test_plugin_mirror_parity.py::OpenClawToolVerbSurfaceTest::test_ts_verbs_match_engine_subparsers` parses `GOC_VERBS` out of `openclaw-plugin/index.ts` and asserts equality with `goc.engine._build_parser()`'s argparse subparsers (order-sensitive). The next subparser added to the engine without updating the TS literal-union turns this test red instead of silently shipping an unreachable verb.
- **Verification**: `reproduce.py` exits 0 ("OK: engine and plugin tool-verb lists agree"). Full regression suite: 234 passed / 0 failed.
- **Audit**: no rubric configured; mechanical fix (two-step list update + drift guard).
- **Tests**: 234 passed / 0 failed / 0 xfailed.

## Closure verification (2026-05-29T16:10:25Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
