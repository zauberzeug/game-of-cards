## 2026-06-07T05:45:00Z — Closure

- **What changed**: `goc/engine.py:2356` — `sort_default` gained an optional
  `by_title` parameter so the near-term-flow tiebreak counts live downstream
  cards across the full deck, not just the filtered subset being sorted. The
  four call sites that hand it a subset (`render_board` engine.py:2672, the
  leverage line engine.py:2771, `render_active_notice` engine.py:2793,
  `_cmd_default` engine.py:3190) now thread the full-deck `by_title` they
  already hold. Docstring updated to stop equating a filtered-out-but-live
  target with a genuinely dangling edge.
- **Verification**: `reproduce.py` exits 0 — `goc --status open`-style sort of
  the open subset now orders `a-open-two-live` before `x-open-one-live`
  (live_direct A:2 X:1) instead of the age-broken `x, a`. New regression test
  `tests/test_sort_default_full_deck_tiebreak.py` (2 cases: filtered-out live
  target counts; genuinely dangling edge still counts 0). Full suite: 404
  tests OK. `goc validate` exit 0.
- **Audit**: PASS — no principle touched, mechanical fix (aligns the tiebreak
  axis with the value axis, which already runs on the full deck; restores
  consistency rather than choosing a new policy).
- **Project impact**: n/a

## Closure verification (2026-06-07T05:33:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-06-07 — Closure' present
