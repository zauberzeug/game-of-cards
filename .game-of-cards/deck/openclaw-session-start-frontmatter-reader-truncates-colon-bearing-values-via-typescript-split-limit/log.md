## 2026-05-29T23:00:00Z — Closure

- **What changed**: `openclaw-plugin/index.ts` — added `frontmatterTail` helper (uses `indexOf(":")` + `slice(i+1).trim()`) and switched all four `split(":", 2)[1].trim()` call sites in `findActiveCards` to use it; helper docstring names the Python `split(":", 1)[1]` contract being mirrored and the ECMA-262 split-limit trap that motivated the helper. Also fixed `reproduce.py`'s verdict logic — it gated post-fix exit 0 on a Python-simulated `js_parses` that always reflected the broken split semantic, so the script could not return 0 even after the fix; the corrected gate is `len(matches) == 0` (source-state check).
- **Verification**: `reproduce.py` exit 0 (post-fix; 0 buggy call sites); `npx tsc --noEmit` from `openclaw-plugin/` exit 0; `uv run python -m unittest discover -s tests` 237 passed; generalization grep across `*.ts`/`*.tsx` confirms no other call site uses `.split(<sep>, N)[N-1]` against colon-bearing input.
- **Audit**: PASS — no rubric configured; mechanical fix (cross-host parity restoration: TS frontmatter readers now match Python `split(":", 1)[1]` contract documented at `goc/templates/hooks/deck_session_start.py:81`).
- **Project impact**: n/a
- **Tests**: 237 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-05-29T22:56:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-29 — Closure' present
