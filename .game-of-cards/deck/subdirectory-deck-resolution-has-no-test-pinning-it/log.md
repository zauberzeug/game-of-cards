# Log — subdirectory-deck-resolution-has-no-test-pinning-it

## 2026-08-11T05:10:38Z — Closure

- **What changed**: `tests/test_subdirectory_deck_resolution.py` (new, 3
  tests) — pins the READ path of `_resolve_deck_root`: every aggregate
  reader addresses the real deck from a nested subdirectory, and a nested
  foreign git tree does not inherit its host's deck.
- **Premise correction**: the card was filed claiming no test in `tests/`
  referenced the function. That was half wrong.
  `tests/test_new_resolves_existing_deck_root.py` shipped inside 3e17e3b3
  itself and was extended by 30355095, already pinning the `goc new` write
  path across four cwd shapes — including the whole write-side boundary of
  DoD item 3. The genuinely unpinned half was the read path, which is
  exactly where the reported consumer failure lives. The README summary and
  body were rewritten in place to say so; the two modules are now documented
  as a complementary pair rather than a duplicate.
- **Verification**: red confirmed in both directions, not assumed. Against a
  copy of the package with `_resolve_deck_root` patched to `return cwd`
  (pre-3e17e3b3), 4 failures — `--status all --json` and `--ready --json`
  return `[]` against an expected `['fixture-card']`, `validate` prints
  nothing, and `goc new` refuses with "no Game of Cards deck found". That
  reproduces the consumer's symptom exactly. Against a copy with the
  foreign-working-tree stop disabled (pre-30355095), 1 failure — the
  boundary test inherits `host-repo-card` across the tree line, proving it
  is a live pin rather than a tautology any resolver satisfies.
- **Audit**: no rubric configured; mechanical fix.
  (`.game-of-cards/hooks/finish-card.md` is comment-only.)
- **Project impact**: n/a
- **Tests**: 951 run — 950 passed / 1 failed. The failure is
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, which
  is pre-existing on main, unrelated to this card (it fails on the live card
  `openclaw-pattern-check-never-fires-on-plain-file-edits` carrying
  `unverified`), and already filed as
  [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/)
  at `human_gate: decision`. Not touched here — the guard on that test
  explicitly forbids widening the row, and the resolution is a human call.
- **Also**: this card was found sitting as an authored `draft: true` scaffold,
  invisible to `--ready`, because the filing session on 2026-08-01 never ran
  `goc publish`. Released with `goc publish` before claiming.

## Closure verification (2026-08-11T05:11:12Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-08-11 — Closure' present
