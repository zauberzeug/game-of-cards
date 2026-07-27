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
