# Journal

## 2026-08-11 — surfaced during a pull-card session on an empty ready queue

Found while auditing after `goc --ready` came back empty (every `human_gate:
none` open card carried an impediment overlay). The predecessor card
`empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card`
had closed hours earlier, so the `hidden_drafts` recount it introduced was the
newest code on the read path and the natural place to probe.

## 2026-08-11 — guard sensitivity confirmed

The DoD's PROCESS item. `goc/engine.py` was reverted to `HEAD` (both halves of
the fix removed at once — with `run_query` in place but `live_impeded` still
lacking the keyword the call would raise `TypeError`, so a half-revert measures
nothing) and `HiddenDraftCountSpansTheWholeQueryTest` re-run:

```
Ran 7 tests in 0.008s
FAILED (failures=3, errors=2)
```

The three failures are the load-bearing ones:

- `test_draft_without_an_overlay_is_not_counted_under_waiting` — the clause
  appears for a draft with no overlay at all.
- `test_draft_outside_the_closed_since_window_is_not_counted` — same for a
  draft closed months outside the window.
- `test_the_two_waiting_shapes_do_not_render_identically` — the collapse
  itself: an impeded draft and an unimpeded one produce byte-identical
  sentences.

The two errors are `TypeError: live_impeded() got an unexpected keyword
argument 'include_drafts'`, from the pins that assert the flag is opt-in.

Restoring the fix returns the whole file to `Ran 29 tests ... OK`, so the two
true-positive controls (`test_actively_impeded_draft_is_still_counted_under_waiting`,
`test_draft_inside_the_closed_since_window_is_still_counted`) pass in both
directions of the change — they are what stops "suppress the clause under those
two flags" from being an accepted fix.

## 2026-08-11T05:52:00Z — Closure

- **What changed**: `goc/engine.py:2570` — `live_impeded` gains the
  `include_drafts` keyword (the third and last axis the draft gate is inlined
  on); `goc/engine.py:3998` — the three query stages collapse into one
  `run_query(*, include_drafts=False)` closure that both the real query and the
  zero-match draft recount call, so the count reflects the whole predicate
  instead of `filter_cards` alone.
- **Verification**: `reproduce.py` exit 1 → 0 (decks A and B lose the false
  clause, control C keeps its true one); suite 951 → 958 tests (+7), and the
  new class goes 3 failures + 2 errors when the fix is reverted.
- **Audit**: PASS — no rubric configured
  (`.game-of-cards/hooks/finish-card.md` is empty); mechanical fix continuing
  the `include_drafts` pattern the predecessor card established.
- **Project impact**: n/a
- **Tests**: 957 passed / 1 failed / 0 xfailed. The one failure is
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, red on
  `main` before this change (verified at session start, same offending card
  `openclaw-pattern-check-never-fires-on-plain-file-edits`) and tracked by
  [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/),
  which is parked on a human decision gate.
- **Also green**: `uv run goc validate` exit 0;
  `scripts/sync_plugin_assets.py --check` byte-clean across the four
  `engine.py` copies.
- **Bundled with**: none

## Closure verification (2026-08-11T05:32:18Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-11 — Closure' present
