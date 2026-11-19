## 2026-11-19T04:46:49Z — Filed as a fix-through from the triage card

Surfaced by the survey of every engine verb in a repo with no deck, run while
working
[goc-triage-reports-no-parked-cards-in-a-repo-that-has-no-deck](../goc-triage-reports-no-parked-cards-in-a-repo-that-has-no-deck/).
That card's log.md has the full table. It clears the fix-through bar: gate-free,
one call in the file the triage fix touches plus a case in the same test
module, and close to the loaded context.

- **Dedup**: the deck's READMEs grepped for `quality-pass` together with
  `no deck`, `missing deck`, `deckless` or `without a deck`. Every title holding
  `quality-pass` was checked too. Nothing covers a missing deck.
- **Verdict**: `reproduce.py` exits 1 on `476f0b2f` with the triage fix in the
  working tree. Neither `goc quality-pass` nor `goc quality-pass --status all`
  prints the notice.

## 2026-11-19T04:52:24Z — Closure

- **What changed**: `goc/engine.py` `_cmd_quality_pass` calls
  `_note_missing_deck()` just before `load_all_cards()`. That is the helper
  the triage card introduced, so the notice line matches the queue view's byte
  for byte. Plugin mirrors are re-synced.
- **Verification**: `reproduce.py` exits 0. Both `goc quality-pass` and
  `--status all` print the notice, with exit 0 and the zero-card stdout
  unchanged.
- **Tests**: `tests/test_missing_deck_notice.py` gains
  `test_quality_pass_names_the_missing_deck_like_the_queue_view`, which fails
  before the fix, and `test_quality_pass_stays_silent_on_an_existing_deck`.
  The module runs 10 tests OK. The full suite (`uv run python -m unittest
  discover -s tests`) ran 1516 tests OK.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a.
- **Other cards**: none describes this defect. While surveying `--llm` with no
  deck, this card found that Layer 2 calls `claude -p` on an empty selection.
  That defect is unrelated to the notice and is filed as its own card.

## Closure verification (2026-11-19T04:52:25Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 3/3 ticked
- [x] log-md-closure-entry — '## 2026-11-19T04:52:24Z — Closure' present
