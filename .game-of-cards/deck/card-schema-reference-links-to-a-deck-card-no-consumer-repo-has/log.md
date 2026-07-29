## 2026-07-29 — Filed from a pull-card session that found the ready queue empty

`goc --ready` returned nothing: the three `human_gate: none` open cards all
carry an active `waiting_on` overlay (`external`, `deferred`, `deferred`), so
`Skill(pull-card)`'s empty-queue branch handed the session to
`Skill(audit-deck)`.

The lead came from a mechanical sweep rather than a reading pass: resolve every
relative markdown link in the repo against the file that holds it and report the
ones that miss. Thirty-one misses in the skill trees, thirty of them placeholder
targets (`../<title>/`, `comparison-matrix.html`) that are meant to be
unresolvable. The thirty-first was real, and it was real for a reason the sweep
did not itself explain: the hit was in the *source-of-truth template*, while the
five mirrors of the same authored line came back clean.

That asymmetry turned out to be the whole story. `goc/templates/skills/<name>/`
is four directories below the root; every mirror tree — `.claude/skills/`,
`.codex/skills/`, `claude-plugin/skills/`, `codex-plugin/skills/`,
`openclaw-plugin/skills/` — is exactly three. The link was written with three
`../` segments, so it resolves from all five mirrors and misses from the file
that generates them. A reviewer looking at any rendered copy in this repo sees a
working link to a real card.

Dedup before filing. `goc --status all` grepped for the offender's identifying
strings (`advanced-by-treated-as-hard-prerequisite`, `cites`, `nonexistent`,
`reference`) and the eight `disproved` bodies were read for a rebuttal; none
exists. The nearest open card,
`next-card-reclassify-checklist-cites-nonexistent-docs-framework-path`, is the
same *shape* — a shipped skill body carrying a path only goc's own repo could
satisfy — at a different site, and it is prose naming a directory rather than a
resolvable link. It stays open on its own terms and is cross-referenced from the
body; no `advances` edge, since neither card's closure delivers the other's
value.

## 2026-07-29 — Fixed through in the same session, and closed

Worked to close under `Skill(pull-card)` § "Fixing what you surface" rather than
left in the queue. The finding cleared all four bars: gate-free (the fix is the
file's own convention eight lines below the offender, not a pick between
credible alternatives), single-site (one template plus mechanically regenerated
mirrors), not an Nth-instance meta-fix, and sitting in context this session had
already loaded to diagnose it.

Two decisions worth recording.

**Why drop the link rather than repair the path.** Adding a fourth `../` would
fix the source tree and leave every consumer with a link into their own deck,
pointing at a card they have never had — the larger half of the defect, and the
half no in-repo check can see. There is no path spelling that works, because the
target is goc's card, not the reader's. The bare backticked title keeps the
provenance searchable and promises nothing.

**Why the guard is anchored on link syntax.** Several shipped skills print
`.game-of-cards/deck/` legitimately — kickoff's `ls` probe, the deck skill's verb
table, retrospective's `cat` example. Those instruct a reader to act on their own
deck and are correct in every repo. Matching the bare path would flag all of
them; matching `](…)` separates naming a directory from promising a file. URL
targets are excluded for the same reason: they resolve for every reader or none,
independent of the install.

Before closing, the guard was checked against a reintroduced offender — with the
original line restored in the template,
`test_no_shipped_skill_body_links_into_a_deck` fails and names
`card-schema/reference.md:219`, then passes again once reverted. This is the
requirement `static-source-guards-never-prove-they-can-catch-an-offender` puts on
new static guards, and it is why the suite also pins that each swept tree really
holds skill bodies: a renamed tree would otherwise turn the sweep into a vacuous
pass.

Closing evidence: `reproduce.py` exits zero, 862 tests pass (five new),
`sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` both
exit zero, `goc validate` is clean across 687 cards.

## 2026-07-29 — Connected to the static-source-guards family root after closure

The Stop-hook generalization check fired on this closure. Dedup found the root
already filed — `static-source-guards-never-prove-they-can-catch-an-offender` —
so this is a connection, not a new umbrella.

What it contributes is a third registration element, and it comes from the
compliance side rather than from a defect: writing a guard that satisfies the
root's requirement surfaced a failure mode the root's Option B design cannot
reach. Both corrections already recorded there are about the *sample* (a clean
near-miss beside the offender; asserting which finding, not a boolean). Neither
covers a scanner that is sensitive, specific, and pointed at nothing.
`tests/test_skill_template_deck_links.py` sweeps six hardcoded tree paths; rename
one and it drops out of coverage while `assertEqual([], hits)` stays green. A
generated sensitivity case runs over a synthetic sample, non-empty by
construction, so it cannot see the production corpus go empty.

Hence the corpus floor, `test_the_trees_are_actually_being_swept`. The element is
not new to the repo — `tests/test_card_authoring_rules.py:399` has carried it
since the card-language guard landed — but it had to be rediscovered here rather
than inherited, which is itself an argument against the root's Option A.

Recorded in the root's "Sibling property" section as the third connected
instance. No `advances` edge: a shared decision, not value flow into a card that
is already closed — same call as the two prior connections.
