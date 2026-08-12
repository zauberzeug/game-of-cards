# log

## 2026-08-12T05:12:00Z — Closure

- **What changed**: `goc/engine.py:4095` — the zero-match hidden-draft
  recount lost its `status != "all"` entry guard. The guard read the draft
  gate off `filter_cards` alone, where `--status all` really is inert, and
  missed that `card_is_ready` (`engine.py:2485`) and `live_impeded`
  (`engine.py:2600`) drop drafts without consulting the status filter at
  all. Since `--waiting` / `--closed-since` / `--board` auto-extend an unset
  `--status` to `all` (`engine.py:3980`), the flagless `goc --waiting` took
  the skipped branch on every invocation.
- **Verification**: `reproduce.py` flipped 0 → 1. Two pairs, each the same
  deck rendered twice: flagless `goc --waiting` and `goc --ready --status
  all` now print the same `1 unauthored draft scaffold hidden` clause their
  `--status open` counterparts always did. Publishing the scaffold makes the
  identical query list the card, which is what makes the previously-omitted
  clause a false negative rather than a correctly-withheld one.
- **Guard sensitivity**: restoring `and status != "all"` turns exactly four
  of the six new cases red —
  `test_flagless_waiting_names_the_scaffold_it_is_hiding`,
  `test_ready_at_status_all_names_the_scaffold_too`,
  `test_the_two_flagless_waiting_shapes_do_not_render_identically`,
  `test_widening_to_all_does_not_change_what_waiting_reports`. The other two
  are true negatives and stay green under both shapes, which is the point:
  they are what stops the fix degenerating into "always count under `all`".
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is an empty stub); mechanical fix. It removes a stale conditional and adds
  no new `include_drafts` call site, so it is independent of whichever
  mechanism `draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it`
  eventually picks.
- **Project impact**: n/a
- **Tests**: 964 run, 963 passed, 1 pre-existing failure unrelated to this
  card (`test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`,
  reproduced on `8fa21b3c` in a clean worktree before any change here; it
  reports `openclaw-pattern-check-never-fires-on-plain-file-edits` carrying
  `unverified` while failing that tag's row). `tests/test_empty_query_result_line.py`
  itself: 35 passed, 0 failed. Plugin mirrors re-synced —
  `scripts/sync_plugin_assets.py --check` clean, `tests/test_plugin_mirror_parity.py`
  24 passed.

## Why the predecessor did not catch this

`zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface`
fixed the *body* of the recount to replay all three query stages instead of
`filter_cards` alone. Its entry condition was left keyed to the first stage,
so on `--waiting` and `--ready --status all` the corrected pass is never
reached. Every regression case that card added passes `status_flag="open"`
explicitly (`tests/test_empty_query_result_line.py:457`, `:464`, `:471`),
which is precisely why the status the command line actually resolves to went
unexercised. The new class leaves the status filter unset on purpose and
pairs each rendering against its `--status open` twin.

## Closure verification (2026-08-12T05:05:58Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 6/6 ticked
- [x] log-md-closure-entry — '## 2026-08-12 — Closure' present
