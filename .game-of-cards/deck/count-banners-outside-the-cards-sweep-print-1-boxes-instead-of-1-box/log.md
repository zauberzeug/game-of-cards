## 2026-07-27T01:31:26Z: renamed from quality-pass-applied-line-prints-1-titles-instead-of-1-title

## 2026-07-27T01:49:00Z — Closure

- **What changed**: `goc/engine.py:1200` — `_cards_noun(count)` generalized to
  `_plural(count, singular, plural=None)`; its 8 existing call sites rewritten
  to `_plural(…, "card")` and the 9 unreachable interpolations (7 sites:
  1723, 2240, 4255×3, 4293, 4375, 5036, 6214) routed through the same
  definition. `tests/test_count_message_pluralization.py` widened from
  `\{len\(…\)\}\s+cards?\b` to any interpolation + optional 2-word adjective
  run + an explicit countable-noun vocabulary, with f-string fragments spliced
  so a count and its noun split across source lines cannot hide either.
- **Verification**: both reproduce scripts exit 0 —
  `count-banners-…`'s static scan drops 9 offenders → 0 and its live probe
  prints `1 unchecked DoD box`; the closed sibling's still passes (its
  `SAFE_TERNARY` was extended to recognise `_plural(`, which the rename would
  otherwise have made blind). Falsification against the real engine:
  reintroducing site 4293 (non-card noun) and site 2240 (adjective between
  count and noun) turned `NoHardcodedPluralTest` red and it named both —
  `goc/engine.py:4304 [unchecked DoD boxes]` and
  `goc/engine.py:2248 [blocked cards]` — then the revert was undone and the
  guard went green. `GuardCatchesBothMissedClassesTest` pins that same reach
  permanently against synthetic source, so the proof does not depend on
  anyone repeating the manual revert.
- **Audit**: PASS — no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 810 passed / 0 failed / 0 xfailed (`uv run python -m unittest
  discover -s tests`; 808 before this card's two new cases — the guard's
  fragment-splice case and the triage `+1 more line` case — plus the
  `_plural` unit cases replacing the `_cards_noun` ones).
  `uv run goc validate` exits 0 with 0 errors.
- **Notes**: two tests changed by design, not regression.
  `tests/test_done_bundle.py::test_bundle_refuses_unchecked_dod` built a
  `dod_open=1` fixture and asserted the plural substring; it now asserts the
  exact singular refusal. `tests/test_triage_decision_preview_overflow.py`
  covered site 6214 only in the plural (its fixture hides 2 lines), so a
  7-line fixture asserting `… +1 more line` was added — otherwise that site
  would have been fixed with no end-to-end proof.
  `goc/templates/skills/finish-card/SKILL.md` documented the refusal as
  `<n> unchecked DoD boxes` and now reads `box(es)`; plugin mirrors and the
  OpenClaw port were regenerated (`scripts/sync_plugin_assets.py`,
  `scripts/port_skills_to_openclaw.py`, both `--check`-clean afterwards).

## Closure verification (2026-07-27T01:49:19Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-27 — Closure' present
