## 2026-06-22T09:35:00Z — Closure

- **What changed**: `goc/templates/hooks/deck_session_start.py` — factored a quote-preserving `_comment_free_tail`, made `_scalar_or_none` and `_card_waiting_on` apply null/bool/int coercion only to *unquoted* tokens; mirrored in `openclaw-plugin/index.ts` (`scalarOrEmpty` / `waitingOnScalar`). A quoted `waiting_on: "true"`/`"42"`/`"null"` (and `waiting_until: "null"`) now stays a live string reason, matching the engine.
- **Verification**: reproduce.py exits 0 (was 6 divergences); quoted forms impede, unquoted forms still resolve to absent.
- **Audit**: PASS — no principle touched, mechanical fix (mirrors engine's `isinstance(v, str)` / yaml-lite bare-vs-quoted coercion contract).
- **Project impact**: n/a
- **Tests**: 513 passed / 0 failed (OpenClaw TS matrix test ran, not skipped).
- **Bundled with**: n/a

## Closure verification (2026-06-22T09:26:32Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-22 — Closure' present
