
## 2026-08-10 — Filed, and connected to its root cause

Filed from the deck hygiene pass that repaired 389 drifted citations across 114
open cards (commit 69e1e4f2). The repair is what exposed the check: the pass
ran the specified `≤ EOF` test first, got a clean report on all 706 citations,
and only found the rot by anchoring each cite to the text it named at the card's
creating commit.

Connected as a cross-reference to
`static-source-guards-never-prove-they-can-catch-an-offender`, recorded there as
a fifth surface. No `advances` edge, per that card's stated convention for
evidence connections on an open decision.

## 2026-08-10T05:02:27Z — Closure

- **What changed**: `goc/templates/skills/refine-deck/SKILL.md:103` — the
  `### Defunct file:line citations` section now specifies an anchor comparison
  (text at the cited line in HEAD vs. the text the card anchored on at its
  creating commit) plus the four-step repair recipe, and says outright that an
  in-range line number is no evidence a cite is current. Long form moved to
  `goc/templates/skills/refine-deck/reference.md:111` § "Citation anchor check";
  all five mirrors regenerated.
- **Verification**: `reproduce.py` exits 0 — over 806 citations replayed at each
  open card's creating commit, the specified check reports 728 of 728 drifted
  cites (521 auto-repairable, 207 residue handed to a human: 92 trivial,
  87 ambiguous, 28 anchor-absent) with 0 false positives on the 78 that are still
  correct. The bounds test it replaces reports 0 of 728. Both mirror guards clean.
- **Audit**: no rubric configured; mechanical fix.
- **Project impact**: n/a
- **Tests**: 934 passed / 1 failed / 0 xfailed. The one failure,
  `test_canonical_tag_rows.test_live_cards_satisfy_every_state_row`, is red at
  HEAD before this change and is tracked by
  `regression-suite-red-on-main-over-the-unverified-tag-row`.

Two design notes worth carrying. The DoD's recall assertion is definitional —
the anchor predicate and the ground truth are the same comparison, which is the
finding, not a flaw — so `reproduce.py` also asserts the two things that are
not: no false positive on unchanged cites (which kills the degenerate
report-everything predicate), and repaired + residue == drifted (which kills a
pass that emits only what it can auto-fix, the same fail-open shape as the
bounds test). It further fails on a population under 100 rather than pass on an
exhausted fixture.

The replayed population grew from 528 to 806 because the script now maps both
endpoints of range cites, as the shipped spec requires. Recall is unchanged in
shape; the figures on this card and on the root-cause card were updated in place
to the wider measurement.

`tests/test_skill_body_size.py` raised the refine-deck cap 10,300 → 11,200 bytes.
The reference sibling took the rationale and the residue table, per that guard's
doctrine; the rule and the recipe stayed in the core, because an agent that has
to follow a pointer to learn the test will run the bounds test it remembers.

## Closure verification (2026-08-10T05:02:47Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-10 — Closure' present

## 2026-08-17 — Post-close evidence: the repair recipe is not idempotent

The 2026-08-17 hygiene pass ran this card's recipe as the second pass over
the deck and found that step 2 is only correct on a first pass. Anchoring at
the card's creating commit reads a number that a *repair* commit authored, so
it resolves unrelated code and then relocates the cite to match it. Measured
at 165 correct citations moved, 2 misplaced, 3 wrongly declined out of 850.

Not reopened — the defect this card fixed (a bounds test that could not fire)
is genuinely fixed, and the content-anchor shape it introduced is right. Only
the choice of anchor commit is wrong. Forward pointer added to the README and
the correction filed as
`second-citation-repair-pass-moves-correct-cites-onto-unrelated-code`, with
the decay rate that makes second passes routine filed as
`file-line-citations-drift-again-within-days-of-every-repair-pass`.
