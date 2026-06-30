## 2026-06-30 — Closure

- **What changed**: `goc/engine.py` `_cmd_triage` now excludes draft
  scaffolds via the shared `card_is_draft` predicate, matching
  `filter_cards` and `card_is_ready`. Previously its hand-rolled
  candidate filter (`status == "open" and human_gate != "none"`) leaked
  `draft: true` cards filed with `--gate decision`/`--gate session` into
  both the text and `--json` "Waiting on you" views, while every other
  surface hid them.
- **Verification**: new regression test
  `tests/test_triage_hides_draft_scaffolds.py` (text + JSON paths) —
  confirmed RED on the pre-fix comprehension, GREEN after. `reproduce.py`
  exits 0 after the fix (1 before). Full `unittest` suite 670 passed.
  `goc validate` exit 0; plugin mirrors re-synced
  (`sync_plugin_assets.py`) and `engine.py` parity restored across
  claude/codex/openclaw payloads.
- **Audit**: PASS — no project rubric configured (hook empty). The fix
  binds to the established single-predicate contract: `card_is_draft` is
  the one "not yet real" gate every listing surface must consult, so
  triage routing through it (rather than re-reading the flag) is the
  drift-resistant form.
- **Sibling**: `parked-active-cards-are-missing-from-goc-triage` is the
  opposite-direction divergence of the same hand-rolled filter (it drops
  `active` gated cards). Left open — distinct defect, distinct fix.
- **Tests**: 670 passed
