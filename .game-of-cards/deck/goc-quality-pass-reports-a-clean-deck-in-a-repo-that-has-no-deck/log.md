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
