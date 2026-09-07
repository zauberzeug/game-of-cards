## 2026-08-11T04:57:23Z — Closure

- **What changed**: `goc/engine.py` — `render_empty_query_line` (new
  `hidden_drafts` param + clause), `_cmd_default` (recount on the empty path),
  `filter_cards` and `card_is_ready` (new `include_drafts` keyword). The
  zero-match queue line now names the one conjunct no flag can reveal.
- **Scope beyond the filed fix**: the card's Fix section named three edits;
  four landed. `card_is_ready` drops drafts on a second, independent axis, so
  suppressing the conjunct in `filter_cards` alone left `--ready` — the
  pull-card / next-card surface this card's "Why it matters" calls the costly
  one — still reporting a deck of scaffolds as a drained queue. Threaded the
  same keyword through rather than restating the readiness predicate, which
  `card_is_ready`'s own docstring forbids. Default unchanged, so the
  `card_is_workable_for_scheduler` coupling invariant
  (`tests/test_scheduler_workable_predicate_coupling.py`) is untouched and
  stays green.
- **Verification**: `reproduce.py` exits 0 (was 1); the two decks it builds
  now render differently (`messages identical: False`). Confirmed end-to-end
  through the real CLI on a scratch repo: `goc` -> `No cards match (status:
  open; 3 unauthored draft scaffolds hidden — author, then `goc publish
  <title>`).`, and `goc --ready` names 1 (only the gate-none scaffold), while
  `goc --tag infra` and a genuinely empty deck gain no clause at all.
- **Guard sensitivity**: reverting the clause emission in
  `render_empty_query_line` turns 3 of the 10 new tests red
  (`test_a_deck_of_scaffolds_does_not_read_as_a_drained_deck`,
  `test_the_count_is_singular_for_one_scaffold`,
  `test_ready_queue_names_hidden_scaffolds_too`); restored and re-verified
  green.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 948 passed / 1 failed / 0 xfailed. The single failure is
  `tests/test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`,
  red on `main` before this work and tracked by
  [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/)
  (`human_gate: decision`, unrelated card). Baseline was 938 tests with the
  same one failure; this closure adds 10 and breaks none.
  `uv run goc validate` exits 0; `scripts/sync_plugin_assets.py --check` is
  byte-clean across all four `engine.py` copies.

## Closure verification (2026-08-11T04:57:59Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-11 — Closure' present
