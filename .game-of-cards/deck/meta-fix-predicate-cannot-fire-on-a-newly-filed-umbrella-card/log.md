
## 2026-08-03T03:05:00Z — Filed from a refine-deck hygiene pass

Surfaced by Step 2 § "Tags without firing predicates" while sweeping the
text-matchable rows. The other evaluable rows are clean on the live
population — `documentation` fires on 27 of 27, `test` on 1 of 1, and all 14
`unverified` cards correctly lack a working `reproduce.py`. Only `meta-fix`
fails, on 4 of 54.

Two of the four (`a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach`,
`static-source-guards-never-prove-they-can-catch-an-offender`) were surfaced
independently by the same pass's orphaned-dependency sub-check 2, which
prescribes the same disposition — strip — for a zero-edge card with no
literal. Neither is mistagged: the first is a governing card whose grouping is
*deliberately* edgeless and whose subject is that very fact, and the second is
an umbrella whose family members are four guards in test files rather than
cards, so there is no roster to wire. Sub-check 2's genuine-versus-mistagged
fork has no branch for an umbrella whose family is code sites.

**This pass declined the strip and filed instead.** That decision is recorded
here because it is not what the skill instructs: the row is fully evaluable
and plainly fails, so the documented mechanical action is to strip. Nothing
in the contract would have stopped a compliant sweep from removing the tag
from all four.

Gate left at `none` per the run's operating instructions (autonomous runner,
no human in the loop) even though `## Fix` offers three paths. The third —
making the sweep report rather than strip — is the one the recurrence argues
for and the one neither predecessor considered; a later reader may reasonably
raise the gate to `decision` to pick between it and a second widening.

Filed with `advances: doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`,
following the `story` row card's precedent: a predicate in a doc is a doc
claim about the deck, and nothing re-scores it between refine passes.
