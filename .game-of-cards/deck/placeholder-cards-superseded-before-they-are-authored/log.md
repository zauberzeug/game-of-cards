## 2026-06-28T17:57:27Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The guard is clear in intent — automation must not treat an unauthored scaffold as a real,
deduplicable card — but the mechanism is a design choice:

- **Option A — engine guard on terminal transitions.** `goc status <card> {superseded,disproved}`
  (and the typed-edge writer) refuses, or hard-warns, when the target card is still a placeholder
  (DoD equals the generated `- [ ] (replace with real criteria)` and/or body equals the
  `(write the design doc here)` stub). Path-independent: protects against any caller, not just the
  loop. Recommended; small and precise.
- **Option B — first-class draft state.** `goc new` marks the card `draft` (or an `authored: false`
  flag); queue/dedup/supersede paths skip drafts; a card leaves draft when it gains a real DoD/body
  (or via an explicit `goc publish`). Bigger surface, but makes "not yet real" explicit everywhere
  and lets `auto_commit` keep committing safely (a committed draft is still skipped).
- **Option C — defer the commit, not the card.** Teach `auto_commit` / the documented auto-commit
  pattern to exclude placeholder cards until authored, so the scaffold never reaches shared state.
  Matches the "working tree is for incomplete work" intent, but only helps consumers that commit
  through goc — an external auto-commit service still needs A or B.

Likely best: **A now** (cheap, robust, protects existing decks), with **B** considered if drafts
warrant first-class modelling. C alone is insufficient because external auto-commit services bypass
goc.

Once chosen, the DoD becomes: a regression test that the selected guard fires on a placeholder card
and does not fire once the card is authored, plus the mechanical change in `goc/engine.py` (and the
schema/skill docs if a draft state is introduced).


## 2026-06-29T04:06:45Z: decision recorded

Implement all three as defense-in-depth — A: engine guard rejecting terminal transitions (superseded/disproved) on placeholder cards; B: first-class draft state that queue/dedup/supersede skip; C: auto_commit excludes unauthored placeholder cards. — Maintainer call — B's authored/draft flag becomes the shared basis A and C key off (more robust than matching placeholder strings); A also protects legacy decks and non-goc callers, C cuts commit noise from unauthored scaffolds (the stated reason C was added).. Gate decision → none.
