## 2026-06-21T00:00:00Z — Closure

- **What changed**: `openclaw-plugin/index.ts` — added `NULL_LITERALS` set + `scalarOrEmpty` helper (mirrors the Python hook's `_scalar_or_none` / `yaml_lite._NULL_SET`) and routed the `waiting_on` / `waiting_until` frontmatter reads in `findActiveCards` through it, so `waiting_on: null` / `~` / `Null` / `NULL` resolves to absent instead of the truthy string `"null"`.
- **Verification**: `reproduce.py` exit 0 — Python hook and OpenClaw TS now agree `impeded=False` for all 4 explicit-null literals (was 4/4 DIVERGES). New null-literal cells added to `tests/test_openclaw_session_start_hook.py` (reader path `scalarOrEmpty ∘ frontmatterTail` + `isImpeded`).
- **Audit**: PASS — no project rubric configured (hook empty); mechanical port-parity fix mirroring an existing Python primitive.
- **Project impact**: n/a
- **Tests**: 495 passed / 0 failed
- **Bundled with**: n/a

## Closure verification (2026-06-21T10:20:08Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-21 — Closure' present
