
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

## 2026-08-03T05:30:00Z — Unit of repair picked: classify the rows, and stop the sweep from stripping

The DoD asked for a pick between three shapes. **Picked 2 + 3.** They are not
alternatives: option 3 is orthogonal to which predicate is chosen, and option 2
alone would leave the next under-measured row destructive.

**Why not option 1 (widen again).** Beyond the argument already in the body,
it is empirically insufficient. Dropping the "neighbour must also be tagged"
requirement from the edge clause — the smallest widening that reaches the two
high-edge failures — leaves
`a-shared-tag-groups-a-cluster-that-no-edge-walk-can-reach` still failing, and
that card cannot be reached by any edge clause because a deliberately edgeless
grouping *is* its subject. Widening the edge clause that far also makes the row
fire on any card with two edges, i.e. most of the deck, so the row stops
discriminating in exchange for still not covering its own population.

**Why option 2 was taken as a classification, not a frontmatter marker.** The
filing floated "a frontmatter-level marker the author sets when filing an
umbrella". Rejected in that form for two reasons. It is circular unless the
marker carries information the tag does not — and the version that does carry
information (a `family:` roster field) is a public schema change: `goc/schema.yaml`,
the validator, the emitter, every consumer, plus a backfill of 54 live cards
before the DoD's first item could pass. That is a decision-class,
cross-repo-surface change riding on a `contribution: low` card. The
classification reaches the same place — the satisfier stops depending on prose
archaeology, and an umbrella meets its row by construction — with no new field
and no backfill.

**The trap avoided.** A "by construction" satisfier is one edit away from being
tautological: make the tag its own satisfier and every card passes, which is
exactly how the predecessor's closure certified 45 of 45 while five cards
failed. So the split had to be principled, and it is: `state` rows are
satisfied out of frontmatter, edges, or card files, and nothing else is. That
is a real, checkable line, and CI now scores those three rows against the live
population — `bug` (143 live), `epic` (6), `unverified` (14), all clean —
rather than asserting they are.

Two consequences worth recording, because they are visible costs of this pick:

- **Six of nine rows are now `judgment`,** including `documentation` and
  `test`, which were previously scorable in principle. This is not a
  concession; scoring `documentation` by its own row's patterns fails 8 of 28
  live cards, so it was a fourth instance of the same defect waiting for
  someone to measure it. Net enforcement went *up*: the three rows that can
  bear it moved from an every-N-weeks destructive sweep to always-on CI, and
  the rest moved from a wrong mechanical verdict to a reported one.
- **Two hot-path skill caps were raised** in `tests/test_skill_body_size.py`
  (card-schema 12000 -> 12800, refine-deck 10000 -> 10300). Both files sat
  within 5 bytes of their cap, so any addition needed either a trim or a bump.
  The rationale — the three measurements, the default aid surface — went to the
  reference siblings as that guard prescribes; what stayed in the hot path is
  the `check` column and the two lines saying what `judgment` implies, which a
  reader of the table cannot act on from a pointer. The bump is recorded in the
  constant's comment rather than left as an unexplained number.

`reproduce.py` was rewritten rather than deleted. It cannot score the new row —
that is the point of the fix — so it asserts the two properties that make the
old failure impossible, and it still prints the population the original
predicate cannot fire on. Confirmed it exits 1 at the pre-fix state (row
classified `state`) and 0 after. Both new guards were mutation-tested: flipping
`meta-fix` back to `state` reddens two cases, restoring the strip instruction
reddens a third.

Scope note: the DoD named four surfaces. Two more restated the same contract
inline and were corrected in the same pass — orphaned-dependency sub-check 2
(whose genuine-versus-mistagged fork prescribed strip on a missing literal, and
had no branch for an umbrella whose family is code sites) and the Step 4.5 note
listing predicate-failing tags among the mechanical-apply findings. The `story`
card's closure is the precedent for expecting more than the named set.

## 2026-08-03T05:32:00Z — Closure

- **What changed**: `goc/templates/skills/card-schema/SKILL.md` § "Canonical
  tags" — the tag table gained a per-row `check` column (`state` | `judgment`),
  `meta-fix` moved to `judgment` with its literal/roster/edge patterns demoted
  to aids marked "none required", and `Skill(refine-deck)`'s sweep action on a
  non-firing row changed from *strip* to *report* across four surfaces.
- **Verification**: `reproduce.py` exits 0 (exits 1 at the pre-fix state);
  `tests/test_canonical_tag_rows.py` scores 3 `state` rows over the live
  population — `bug` 143/143, `epic` 6/6, `unverified` 14/14 — and its 5
  `OFFENDERS` cases each stay rejected; mutation-tested both new guards
  (reclassify `meta-fix` → 2 red, restore the strip instruction → 1 red).
- **Audit**: no rubric configured; mechanical fix. Not literally mechanical
  though — the closure binds the asymmetry `refine-deck`'s `reference.md`
  § "Tag sweeps" already argued (an under-firing predicate must cost output,
  not curated data) and makes the instruction follow the argument.
- **Project impact**: n/a
- **Tests**: 897 passed / 0 failed / 0 xfailed. `uv run goc validate` exit 0
  (pre-existing UNTAGGED_DOD_ITEM warnings on other cards, unchanged);
  `sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check`
  green; `check_card_language.py` clean over 700 cards.
- **Bundled with**: n/a

## Closure verification (2026-08-03T05:47:44Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-08-03 — Closure' present
