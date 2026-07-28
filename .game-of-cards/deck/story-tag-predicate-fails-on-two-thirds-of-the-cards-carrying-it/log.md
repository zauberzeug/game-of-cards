## 2026-07-27 — Filed from a refine-deck hygiene pass

Surfaced by `Skill(refine-deck)` Step 2 § "Tags without firing predicates".
The pass was scoring tag predicates across the deck when the `story` row came
back failing on 67 of 102 cards — too broad to strip mechanically, and the
skill's own instruction for that category ("strip it") is what makes the
mismatch dangerous rather than cosmetic.

Both branches of the predicate were checked before filing, not just the edge
one. `.game-of-cards/canonical-tags.md` was read directly: it is the unedited
scaffold comment, so no project tag is registered and the deck's vocabulary is
exactly the nine goc-shipped tags. That makes the tag branch unsatisfiable, not
just unused — which is the fact that lifts this above "authors didn't wire
their edges".

Dedup: `goc --status all` grepped for `story` / `epic` / `tag` / `predicate` /
`canonical` / `grouping`. Two closed cards are adjacent and neither covers
this. `meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag` fixed
the same failure mode on a different row and is the resolution precedent;
`no-guardrail-for-canonical-epic-edge-direction` observed the tag branch going
unused from the `epic` side. Both are cross-referenced in the body and both got
a forward pointer per "closure is not frozenness". Neither delivers this card's
value, so no `advances` edge was written — same call, and same reasoning, as
the count-banner/fail-open-guard pair in commit `1145e82e`.

Gate left at `none` per the running instruction for unattended passes: the
three resolutions are all cheap and the pick is a scope judgment, not a blocked
question. It is carried by the first DoD box, and a later reader can raise the
gate.

## 2026-07-27 — Step 3 candidate folded in rather than filed separately

The same pass ran `Skill(refine-deck)` Step 3 (new canonical tag candidates).
Six multi-dozen-card title clusters showed up (`plugin` 58, `hook` 52,
`openclaw` 40, `release` 25, `codex` 17, `yaml-lite` 16), but none of them is a
Step 3 hit on its own terms: Step 3 asks for work "that isn't covered by an
existing tag", and all six are covered by `infra`. What they lack is a
*grouping*, which is this card's option 3 exactly.

Per `Skill(create-card)` Step 2 ("Same root cause as an existing card =
supporting evidence on that card's body ... NOT a new filing"), the counts went
into the body under option 3 instead of becoming a second card. Step 4.5 is
satisfied by that disposition — the candidate is durable, not chat-only.

## 2026-07-27 — Resolved: widen, past what option 1 proposed

Picked **option 1 (widen)**, following the resolution precedent set by
`meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag`: when a
documented predicate disagrees with a deck that is otherwise tagged on purpose,
the document is the defect. But option 1 *as drafted* would not have closed the
card — it kept epic-grouping as the satisfier and merely added the edge branch,
which is precisely the pair the original `reproduce.py` already scored at
35/102. Widening had to go past grouping altogether.

Two measurements over all 681 cards decided what to widen *to*, rather than
guessing:

1. `story` and `bug` are used as a partition. One card of 681 carried both
   (`plugin-install-doesnt-refresh-stale-marketplace-cache`); 482 carry `bug`,
   102 carry `story`, 89 carry neither. A 1-in-681 exception is a slip, not a
   convention.
2. The 67 "failing" cards read uniformly as capability deliveries —
   `add-worker-field-and-filter-to-cards`,
   `cli-output-suggests-next-step-after-each-verb`, `install-claude-harness`,
   `create-project-website-explanatory-illustration`. Not one is a defect
   finding filed under the wrong tag.

So the tag's operative meaning is *what kind of work the card delivers*, which
the `bug` row had been asserting from the other side all along ("not `epic` and
not `story`"). The old row's error was naming a grouping mechanism as the
definition of the tag. Epic membership is real but orthogonal, and the deck
records it with edges — the reading `Skill(create-card)` already teaches.

A useful confirmation that the new reading is the deck's own: it dissolves both
anomalies the filing flagged, without either needing a fix.
`support-external-game-of-cards-state-location` and
`drop-third-party-runtime-dependencies-from-goc` carrying `epic` *and* `story`
was an anomaly only while `story` meant "member of a grouping"; an epic that is
itself a capability delivery is unremarkable. Likewise
`list-game-of-cards-on-anthropic-community-marketplace`, where the two rows
returned opposite verdicts, now satisfies both.

**The refine-deck edit is load-bearing, not scope creep.** § "Tags without
firing predicates" restated the strict title/H1/~2500-char window inline and
instructed the operator to strip any tag failing it. Fixing only the
card-schema row would have left the harm path fully intact: the next hygiene
sweep reads refine-deck, not the row. It now defers to each row's own
predicate, names the judgment-driven rows (`story`, `api-contract`, `infra`) as
not sweepable by text match, and states that "I cannot evaluate this
mechanically" is not "the predicate does not fire". That section had also
silently drifted from card-schema's "unless its row widens the surface" clause,
which the `meta-fix` precedent added and never mirrored here — a second reason
the two files needed reconciling in one pass.

`reproduce.py` was rewritten to score the widened row. It gates only on the
mechanically decidable half — no card carries both `story` and `bug`, an
invariant *both* rows now assert, so the check verifies the pair — and reports
epic-grouping coverage (35/101) without gating on it. Gating on an orthogonal
property is the defect this card is about; re-introducing it in the test would
have been the same mistake one layer down. The remaining clause is a judgment
about card content with no closed-form predicate, which is why refine-deck now
says so explicitly instead of leaving a sweeping agent to infer "unevaluable →
strip".

**Option 3 declined, not dropped.** Registering an epic-grouping tag is no
longer required by this row — grouping is not a satisfier — and it is a
curation decision about this deck's vocabulary rather than a fix to a wrong
predicate. Bundling it would have made a `contribution: low` documentation fix
carry a 58-card retag temptation. It stays available and undamaged: the `epic`
row still offers the branch (correct for consumer repos that register one), and
the Step 3 candidate table is preserved in the body as its input. No follow-up
card was filed — the proposal is durable in this card's body, and filing a
decision-gated card for an option deliberately declined with its data intact is
the "filing exceeds deciding" anti-pattern the deck's own hygiene guidance
warns about. DoD box 4 resolved N/A for the same reason; the box text was left
verbatim with the disposition appended, so the record does not imply
`canonical-tags.md` gained content it did not gain.

Observed and deliberately not filed: the `bug` row over-claims in the opposite
direction — read strictly, "not `epic` and not `story`" says all 89 cards
carrying none of the three should be `bug`-tagged. That is the inverse failure
of this card's and is harmless to the sweep, which only ever strips; the
parenthetical "(default for findings)" already softens the row to a default.
Noted here so a future reader measuring the same table does not mistake it for
an unrecorded third instance of the shape.

## 2026-07-27 — Size caps forced the split, and improved it

First cut wrote the full reasoning inline into both `SKILL.md` files and broke
`tests/test_skill_body_size.py`: card-schema went 11988 → 12222 (cap 12000),
refine-deck 9997 → 10372 (cap 10000). Both files had been tuned to within 12
and 3 bytes of their caps, so any edit to them has to budget for itself.

Raising a cap was never on the table — the guard is backed by a downstream
measurement (31% of a consuming project's session usage went to this plugin)
and its docstring states the contract directly: new edge-case prose belongs in
the sibling `reference.md`, not the hot path. Followed as written. The
card-schema row compressed to "delivers new/changed capability, not a fix;
disjoint from `bug`" (77 bytes, file 11995) and refine-deck's sweep paragraph
came out *shorter* than the wrong one it replaced (file 9996); the reasoning —
why `epic` + `story` is legitimate, why membership is edge-recorded, the two
sweep rules — went into the two `reference.md` siblings.

Worth recording that the constraint improved the result rather than costing
anything. The long inline row would have put a paragraph of nuance in front of
every reader of the table on every invocation, to fix a row most of them will
never sweep. A predicate row wants to be short enough to scan against a card;
the reasoning wants to be somewhere a reader goes deliberately. Dropping the
epic-grouping parenthetical entirely — rather than rewording it — came out of
the same squeeze, and is the cleaner answer to the DoD's "made accurate or
dropped": with grouping no longer a satisfier, the row has no reason to
mention it at all.

Gates: 821/821 regression tests pass, `uv run goc validate` clean over 681
cards, `scripts/sync_plugin_assets.py --check` and
`scripts/port_skills_to_openclaw.py --check` both green (the card-schema and
refine-deck edits propagate to the claude/codex/openclaw payloads and the
in-repo `.claude/` + `.codex/` mirrors), `reproduce.py` exits 0.

## 2026-07-27T04:42:42Z — Closure

- **What changed**: `goc/templates/skills/card-schema/SKILL.md:250` — the `story` row now reads "delivers new/changed capability, not a fix; disjoint from `bug`", replacing an epic-grouping satisfier no card in this repo could meet; `goc/templates/skills/refine-deck/SKILL.md` § "Tags without firing predicates" now scores each tag against its own row instead of restating a fixed text window; reasoning moved to both `reference.md` siblings; `story` stripped from the one card carrying it alongside `bug`.
- **Verification**: `reproduce.py` exits 0 (was 1 on 67/102 cards); 0 of 101 `story` cards carry `bug`; `goc validate` clean over 681 cards; both capped skill bodies back under budget (card-schema 11995/12000, refine-deck 9996/10000).
- **Audit**: no rubric configured; mechanical fix. (`.game-of-cards/hooks/finish-card.md` is an unedited scaffold stub.)
- **Project impact**: n/a
- **Tests**: 821 passed / 0 failed / 0 xfailed
- **Bundled with**: n/a

## Closure verification (2026-07-27T04:42:45Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-07-27 — Closure' present
