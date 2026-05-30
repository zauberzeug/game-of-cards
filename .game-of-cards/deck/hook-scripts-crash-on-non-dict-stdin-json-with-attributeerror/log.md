## 2026-05-30T17:33:38Z — Closure

- **What changed**: added `if not isinstance(data, dict): return 0` guard right after `json.load(sys.stdin)` in `goc/templates/hooks/deck_prompt_router.py:76` and `goc/templates/hooks/pattern_generalization_check.py:190`. Both hooks now return 0 silently on non-dict payloads, matching the JSONDecodeError branch and the sibling `deck_session_start.py` pattern.
- **Verification**: `reproduce.py` shows 0/7 crashes after the fix (was 6/7 before). `uv run goc validate` clean. `uv run python -m unittest discover -s tests` → 328 tests OK.
- **Audit**: PASS — no rubric configured; mechanical fix (boundary guard mirroring existing sibling pattern).
- **Project impact**: n/a.
- **Tests**: 328 passed / 0 failed.
- **Bundled with**: n/a.

## Closure verification (2026-05-30T17:33:48Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-05-30 — Closure' present
