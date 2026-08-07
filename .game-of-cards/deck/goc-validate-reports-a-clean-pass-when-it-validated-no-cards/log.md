# Log

## 2026-08-07 — filed from an audit pass with an empty ready queue

Surfaced while probing `goc install` end-to-end in a fresh repo. After the
install printed its three next-step lines, `goc validate` — the command the
install output names as the way to check cards — printed nothing at all and
exited 0. Running it again from a directory with no `.game-of-cards/` at all
produced identical zero bytes at exit 0, which is the actual defect: the
frontmatter-drift gate cannot distinguish "clean" from "never found a deck".

Deduped against the 708-card deck first. The nearest neighbours are
[empty-queue-view-prints-nothing-instead-of-saying-no-cards-match](../empty-queue-view-prints-nothing-instead-of-saying-no-cards-match/)
(closed three days earlier — same shape one surface over; it swept the *read*
views and stopped at the gate) and
[ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory](../ci-skips-deck-validation-after-deck-moved-to-game-of-cards-directory/)
(open, `human_gate: session`), whose root cause is a shell path guard in
`ci.yml`. Neither covers the engine's silence; this card is why that class of
failure stays invisible once it happens.

## 2026-08-07 — fixed: the zero-card path states its outcome

One branch in `_cmd_validate` (`goc/engine.py`), immediately before the
closing `if errors: sys.exit(1)`. It prints the resolved `DECK_DIR` alongside
"validated 0 cards (structural checks still ran)".

Three shape choices, each made against existing convention rather than taste:

- **stderr, unconditional of `--quiet`.** The advisory warnings above it
  already use stderr, and `--quiet` documents its contract as suppressing the
  per-card `OK` lines on *stdout*. `--quiet` is also where the false green is
  worst — silence is its expected success rendering — so the notice has to
  survive it.
- **Exit code untouched.** A freshly scaffolded repo legitimately holds an
  empty deck, and `Skill(kickoff)` walks a new user straight from
  `goc install` into `goc validate`. Failing there would break the onboarding
  path to fix a signalling problem.
- **No "validated N cards" summary on the non-empty path.** The per-card `OK`
  lines already prove the gate ran; a trailing line would change output for
  every existing caller and add nothing.

### Verification

`reproduce.py` 1 → 0 (2 findings → 0). Probes B (deck scaffolded, no cards)
and C (no deck directory) went from `0 bytes / 0 bytes / (none)` each — and
byte-identical to one another — to distinct sentences naming their own
resolved deck path, at unchanged exit 0. Probe A (this repo's 708-card deck)
is unchanged.

Suite 928 → 935, with the 7 new tests in
`tests/test_validate_zero_card_notice.py` green. Sensitivity checked by
neutering the print to `pass`: 5 of the 7 redden, and the 2 that stay green
are exactly the pins that must not depend on the notice — "a card-bearing
deck is unchanged" and "a real error still exits nonzero".

`uv run goc validate` clean on this repo's own deck (0 errors);
`scripts/sync_plugin_assets.py --check` byte-identical after the three engine
mirrors were regenerated.

**The suite is not fully green, and was not before this card.**
`tests/test_canonical_tag_rows.py::test_live_cards_satisfy_every_state_row`
fails on `main` both before (928 tests, 1 failure) and after (935 tests, 1
failure) this change, over the `unverified` tag row on the live card
`openclaw-pattern-check-never-fires-on-plain-file-edits`. That red is owned by
[regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/),
open at `human_gate: decision` pending a human pick between retagging the card
and rewriting the row. The final DoD item states that boundary rather than
claiming a green suite.

## 2026-08-07T05:58:49Z — Closure

- **What changed**: `goc/engine.py:_cmd_validate` — a zero-card run now names
  the resolved `DECK_DIR` on stderr instead of exiting 0 in silence.
- **Verification**: `reproduce.py` 2 findings → 0; suite 928 → 935 tests with
  the 7 new `tests/test_validate_zero_card_notice.py` cases green; neutering
  the print reddens 5 of those 7.
- **Audit**: PASS — no rubric configured (`.game-of-cards/hooks/finish-card.md`
  is empty); mechanical fix, and the one shape choice it did make (stderr,
  unconditional of `--quiet`) follows the existing warning convention at
  `engine.py:4062-4073` rather than introducing a new one.
- **Project impact**: n/a
- **Tests**: 934 passed / 1 failed (pre-existing
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, owned by
  `regression-suite-red-on-main-over-the-unverified-tag-row`) / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-08-07T05:59:05Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-07 — Closure' present
