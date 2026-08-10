---
title: static-source-guards-never-prove-they-can-catch-an-offender
summary: "Four prohibition guards in tests/ scan a source or doc tree and assert the offender list is empty, but none is ever run against source that DOES offend. `assertEqual([], offenders)` passes identically whether the tree is clean or the scanner has quietly stopped matching, so a guard can die silently and still read as 'convention enforced'. Killing each scanner's regex leaves all four green; the two guards in the same suite that do prove their sensitivity go red. The technique needs no invention — only a scope decision on how far to apply it."
status: open
stage: null
contribution: medium
created: "2026-07-27T01:54:03Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [test, meta-fix]
definition_of_done: |
  - [ ] (replace with real criteria once the approach in `## Decision required` is picked)
---

# Static source guards never prove they can catch an offender

## Location

Four prohibition scanners across two test files:

| Guard | Scanner | Prohibited shape |
|---|---|---|
| `tests/test_guidance_accuracy.py:21` | `_STALE_PATTERN` | the stale `close + commit` phrasing |
| `tests/test_guidance_accuracy.py:218` | `_STALE_BICONDITIONAL` | the stale `No ⏳ ⇒ pullable` claim |
| `tests/test_guidance_accuracy.py:292` | `_STALE_STUB` | the stale `reproduce.py stub` phrasing |
| `tests/test_skill_frontmatter_strict_yaml.py:21` | `NESTED_MAPPING_COLON` | a nested mapping in skill frontmatter |

Three in-tree counter-examples show the fix shape needs no invention:
`tests/test_plugin_mirror_parity.py` carries five `*_is_detected` tests that
feed synthetic drift to its checker; `tests/test_count_message_pluralization.py`
gained four such cases when
[count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box](../count-banners-outside-the-cards-sweep-print-1-boxes-instead-of-1-box/)
closed; and the `reproduce.py` of
[schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen](../schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen/)
(closed 2026-08-02) runs two known-caught controls alongside its two drift
cases.

That third one is worth more than its count, because its controls caught a
live false negative rather than a hypothetical one. The probe's first draft
reported **all four** cases as "caught" — which would have disproved the card
it was written for. The guard under test builds its failure message with
`relative_to(ROOT)` eagerly, on passing calls too, so redirecting the schema
paths to a temp dir without also rebinding `ROOT` made every test error out on
message construction instead of running. Only the controls distinguished
"nothing drifted" from "nothing ran" — the same two-passing-states problem this
card describes, hit in the harness rather than in the scanner. Note that the
mechanism is the one this card's own `reproduce.py` already uses (copy the
guard, rebind `ROOT` to an absolute path), so the hazard travels with the fix
technique: whatever scope gets picked below should treat the baseline/control
line as part of the deliverable, not as optional rigour.

Neither the schema-parity guard nor its predecessor belongs in the offender
table above — `assertEqual(engine, skill)` is fail-closed, so a dead read
raises rather than passing empty. The citation is about the technique, not
membership in the family.

## What's broken

A prohibition guard ends in some variant of

```python
        self.assertEqual([], offenders, "…must not appear…")
```

That assertion has two passing states and cannot tell them apart:

1. the scanned tree genuinely contains no offender, and
2. the scanner no longer matches anything at all.

State 2 arises from ordinary maintenance — the prohibited wording is rephrased,
the file the pattern anchors to is restructured, an escape is dropped, the shape
being scanned for acquires a variant the regex cannot express. Nothing in the
suite distinguishes the two, so a guard can stop guarding at any commit and the
only signal is its continued green.

This is not hypothetical. It is the exact failure the count-banner sweep just
cost two cards to repair. That sweep found its fix set with
`\{len\([^)}]*\)\}\s+cards?\b`, fixed the seven sites the regex matched, and
then installed a CI guard using **the same regex**. The guard's reach was by
construction equal to the sweep's reach, so the nine interpolations the scan
could not express — every non-card noun, plus `{len(cluster)} blocked cards`,
where an adjective sits between the count and the noun — were invisible to
both. The guard reported the convention enforced while `goc done` printed
`1 unchecked DoD boxes`, the most-read error string in the tool.

The distinguishing property is **which way the assertion fails**:

- **Fail-open** — `assertEqual([], offenders)`. A dead scanner produces an
  empty list, which is the pass condition. These are the four above.
- **Fail-closed** — `assertEqual(1, len(matches))` in
  `tests/test_engine_module_singletons.py:27`, or the `assertIn` presence
  checks in `tests/test_skill_documents_optional_fields.py`. A dead scanner
  produces zero matches, which is the *fail* condition. These need nothing;
  they are already self-proving and are deliberately excluded from the table.

## Empirical evidence

`reproduce.py` simulates scanner death: for each guard it rewrites the
prohibition pattern to `re.compile("(?!x)x")` — a regex that can never match —
and runs that guard's own tests against the real tree.

```
baseline — every guard passes on the unmodified tree:
  PASS  tests/test_guidance_accuracy.py  (OK)
  PASS  tests/test_skill_frontmatter_strict_yaml.py  (OK)
  PASS  tests/test_count_message_pluralization.py  (OK)

scanner killed — does anything notice?
  STILL GREEN  tests/test_guidance_accuracy.py::_STALE_PATTERN
  STILL GREEN  tests/test_guidance_accuracy.py::_STALE_BICONDITIONAL
  STILL GREEN  tests/test_guidance_accuracy.py::_STALE_STUB
  STILL GREEN  tests/test_skill_frontmatter_strict_yaml.py::NESTED_MAPPING_COLON
  CAUGHT       tests/test_count_message_pluralization.py::HARDCODED_PLURAL

FAIL: 4 prohibition guard(s) keep passing with a dead scanner — they assert an
empty offender list without ever proving the list can be non-empty:
  tests/test_guidance_accuracy.py::_STALE_PATTERN
  tests/test_guidance_accuracy.py::_STALE_BICONDITIONAL
  tests/test_guidance_accuracy.py::_STALE_STUB
  tests/test_skill_frontmatter_strict_yaml.py::NESTED_MAPPING_COLON
```

The baseline line matters: all three files pass unmodified, so `STILL GREEN` is
a statement about the mutation being undetected, not about a broken harness.
The script modifies nothing in the repo — each guard is copied to a temp file
with its `ROOT` rebound to an absolute path, and the mutation is applied to the
copy.

## Why it matters

This repo leans hard on prohibition guards. The deck already carries a long run
of cards whose finding is "the guard's predicate was narrower than the class it
claimed to enforce" — `title-antipattern-guard-misses-math-symbols-and-underscores`,
`openclaw-skill-porter-context-regex-misses-parenthetical-headers`,
`pattern-generalization-opt-out-regex-misses-quoted-yaml-values`,
`auto-commit-guard-misses-paused-rebase-without-rebase-head-marker`, and the six
`pattern-generalization-mutation-detector-skips-…` cards. Every one of those was
found by a human or an audit pass, never by CI, because a guard with a blind
spot is indistinguishable from a guard with nothing to find.

The cost is worse than an unguarded defect, because it is an unguarded defect
plus a false claim of coverage. The count-banner case is the measured example:
the first sweep's closure recorded the convention as enforced, and the nine
surviving sites then needed a second full card — filing, briefing, fix,
review — to find and repair.

`tests/test_guidance_accuracy.py` is the highest-exposure file in the table.
Its own related root card,
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
covers a **different** failure mode in the same file — claims that never got a
guard at all. This card covers claims that *have* a guard which may no longer
work. The two are complementary, not duplicates: one is absence, the other is
false presence.

## Sibling property: sensitivity is necessary but not sufficient

Connected from three closed instances. Two are the same guard,
[card-language-guard-flags-legitimate-english-as-non-english](../card-language-guard-flags-legitimate-english-as-non-english/)
and
[card-language-guard-misses-german-spelled-with-umlauts](../card-language-guard-misses-german-spelled-with-umlauts/);
the third,
[card-schema-reference-links-to-a-deck-card-no-consumer-repo-has](../card-schema-reference-links-to-a-deck-card-no-consumer-repo-has/),
is a *new* prohibition guard written to comply with this card, and it surfaces a
third registration element from the compliance side rather than from a defect.
The first instance is the counter-example that bounds this card's remedy — and
the reason the decision below should be read as two-sided rather than extended
by a second umbrella card.

`scripts/check_card_language.py` is the one guard in this repo that already
**complies** with this card. Its suite says so outright:

> It also carries the requirement inherited from the card
> `static-source-guards-never-prove-they-can-catch-an-offender`: a static guard
> must demonstrate it can catch an offender, not merely report a clean tree.
> `test_flags_the_historical_offender` and the `RECALL_CASES` table are that
> demonstration; a guard that silently stopped matching would fail them rather
> than passing quietly on a deck that happens to be clean.
>
> — `tests/test_card_authoring_rules.py`, module docstring

It shipped a defect anyway, in the direction sensitivity testing cannot see. Its
`SUFFIX_EXCEPTIONS` set flagged 9 of 26 English `-ung` words — including
`sprung` and `strung`, the bare stems of four forms it *did* exempt — and its
French marker list contained `des`, which lowercases the DES cipher. A card
titled `requests-are-strung-together-without-a-budget` would have had its commit
rejected as German.

Every `RECALL_CASES` entry passed throughout. They could not have failed: a
sensitivity case proves the scanner still *fires*, and a false positive is the
scanner firing. The two failure directions are not merely different, they are
invisible to each other's test.

**Why this belongs here rather than in a fifth umbrella.** The mechanism
question is identical — per-guard opt-in versus a structural registration — so
one decision settles both, and the deck already carries four undecided umbrellas
of this exact shape (this card plus `doc-accuracy-guards-are-opt-in-per-claim-…`,
`draft-gating-is-opt-in-per-surface-…`, `query-flag-validation-is-opt-in-per-flag-…`).
A fifth would be the redundant-umbrella anti-pattern; what is missing is a
decision, not another card.

**What it changes about the options below.** Option B's registration pair
`(scanner, known-offender-sample)` is one-sided by construction: a guard can
satisfy it completely and still reject legitimate input. The pair wants a third
element — `(scanner, known-offender-sample, known-clean-sample)` — so the
generated cases assert both that the scanner fires on the offender and that it
stays quiet on the near-miss. Under Option A the same correction is per-guard
discipline rather than structure, which is precisely the recurrence argument
already made against A.

**A second correction, to the offender element this time.** Registering a sample
is not enough if the generated assertion is `assertTrue(scanner(sample))`. The
second closed instance,
[card-language-guard-misses-german-spelled-with-umlauts](../card-language-guard-misses-german-spelled-with-umlauts/),
is the demonstration: the same guard could not see German spelled with umlauts,
yet both natively-spelled titles in that card's evidence table were already
flagged — one on `berechtigung`, one on `nicht`, each umlaut-free by accident. A
registered offender plus a boolean verdict would have passed against the broken
guard. So the generated case has to assert *which* finding the scanner reports,
and a paired-input guard has to assert the two inputs return the identical
finding — a sample carries no sensitivity of its own, only the assertion over it
does.

**A third correction, to the corpus rather than the sample.** Both corrections
above are about the *sample*. Neither reaches the failure mode where the scanner
is sensitive, the assertion is specific, and the guard is pointed at nothing.
`tests/test_skill_template_deck_links.py`, added when
[card-schema-reference-links-to-a-deck-card-no-consumer-repo-has](../card-schema-reference-links-to-a-deck-card-no-consumer-repo-has/)
closed, sweeps six hardcoded tree paths (`goc/templates/skills`, the two dogfood
mirrors, the three plugin payloads). Rename or move any one and that tree drops
silently out of coverage while `assertEqual([], hits)` still passes — the
identical false-presence this card is about, arriving through scope instead of
through a dead regex. It is not hypothetical for this repo: `deck/` already
became `.game-of-cards/deck/`, and the mirror trees were added one at a time.

Option B cannot catch it. A generated sensitivity case runs the scanner over a
*synthetic* sample, which is non-empty by construction, so it stays green while
the production corpus goes empty. The registration needs a fourth element — a
corpus floor asserting the tree the scanner walks in production still exists and
still holds a plausible number of files. The precedent is in-tree and predates
this card: `tests/test_card_authoring_rules.py:399`
(`test_live_deck_is_actually_being_scanned`, "a clean result must come from real
cards, not an empty glob") is exactly this element, and the new guard's
`test_the_trees_are_actually_being_swept` is its generalization to a multi-tree
scanner.

So the registration Option B should generate from is
`(scanner, known-offender-sample, known-clean-sample, corpus-floor)` — fires,
stays quiet, and is actually looking at something. The third instance is worth
noting for a second reason: it is the first connected here that was **not** a
defect report. The element surfaced while writing a compliant guard, which is
evidence that per-guard discipline under Option A does not converge — the author
has to rediscover each element, and this one was rediscovered rather than
inherited.

The first instance also shows what a clean sample must be worth. Its
predecessor validated the exception set by sweeping the deck's 4,363 live tokens
for matches and finding none — a real measurement that was nonetheless against
the wrong population, because it can only surface false positives the current
corpus already triggers. A registered clean sample has to be a *near-miss the
corpus does not contain* (there `sprung`, `strung`, `des`), not a sample of
present data, or it reproduces the same blind spot with more ceremony.

## A fourth surface: closure verifications, which no option below reaches

Connected 2026-08-03 from
[meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card](../meta-fix-predicate-cannot-fire-on-a-newly-filed-umbrella-card/).
This card's thesis landed outside `tests/` entirely, on the one-shot script a
card runs to satisfy an `EMPIRICAL:` DoD box.

[meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag](../meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag/)
closed on "all 45 open `meta-fix`-tagged cards pass the widened predicate;
zero false positives", from a sweep its log describes as a "per-card README
read". A README read is the whole file, frontmatter included, and every
`meta-fix`-tagged card carries the literal `meta-fix` in its own `tags:`
line — so the literal clause fired on 45 of 45 by construction. Re-running
the row at that same commit against the body alone fails 5 of the 45. The
tell was in the recorded result and nobody read it as one: **the pass count
equalled the population size**, which is what a check that cannot fail
reports.

This is not the fail-open shape in the table above — nothing died, and the
assertion was a positive one. It is the *sample* correction from two sections
up, arriving through the corpus: the surface being searched contained the
marker unconditionally, so `assertTrue(scanner(sample))` held for every
sample. Same two indistinguishable passing states, same green.

**What it changes about the options.** Both are scoped to prohibition
scanners living in `tests/`. Option A adds a sensitivity case beside each
scanner; Option B registers scanners with a harness and meta-tests that every
scanner has a sample. A verification script written inside a card directory to
discharge a DoD box is neither — it is authored once, run once, quoted into a
closure note, and never executed again. It is the *highest*-leverage
unguarded surface in the repo, because its output becomes the record: the
closure figure above was cited as settled fact for 26 days by cards reasoning
downstream of it. Whatever scope is picked has to say whether a one-shot
closure sweep is in it. If it is, the cheapest form of the corpus floor
already exists — a closure check whose pass count equals its population size
should have to say so out loud.

No `advances` edge, for the reason given in the schema-parity note above:
that card is an evidence connection on an open decision, and so is this one.
The successor card carries the fix for the predicate itself; this section
carries only what it teaches about scope.

## A fifth surface: checks specified in prose, which have no callable to register

Connected 2026-08-10 from
[refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file](../refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file/).
That card's check is not code anywhere. It is a sentence in a shipped skill —
`goc/templates/skills/refine-deck/SKILL.md:103`, until 2026-08-10 reading "verify
each cited file exists and the cited line is ≤ EOF" — that an agent re-derives and
executes on every hygiene pass, then reports as a category with no findings.
That successor card closed on 2026-08-10 and the sentence now specifies an anchor
test, so this instance's *predicate* is fixed; what it contributes here is
unchanged, because nothing about the fix gives a prose-specified check something a
harness could register or a meta-test enumerate.

It is fail-open in the table's exact sense: the output is an empty offender
list, and nothing distinguishes "no citation rotted" from "this test cannot
express citation rot". What it adds to the four is that they *could* stop
guarding, whereas this one never guarded. `≤ EOF` is a bounds test for a
displacement problem, so it can only fire when a file shrinks past a cite;
source files grow. Measured recall over the deck's own citations, replayed at
each card's creating commit: **0 of 728** moved citations reported, while the
check called all 806 clean. It had been shipping that answer for the life of
the deck. (The figures read 0 of 482 when this section was written; the
successor's script was widened at closure to map both endpoints of range cites,
which enlarges the population without changing the recall.)

**What it changes about the options.** Both are scoped to prohibition scanners
living in `tests/`, and both attach to a Python callable — Option A puts a
sensitivity case beside it, Option B registers it with a harness and meta-tests
that every scanner has a sample. A check that exists only as prose has no
callable to register and no file a meta-test can enumerate; it is re-derived
from the same sentence by a different agent each run, so its reach is whatever
that agent inferred, and it leaves no artifact behind to audit. This is the
weakest-bound surface of the five: the closure-sweep case above is at least a
script that once existed, while this one is reconstituted from scratch every
time. If the scope includes it, the floor cannot be registration — it has to be
that a specified check ships with a known-offending example the agent is told to
run it against first, so a specification that cannot fire is caught at the point
of being followed rather than after a deck has rotted underneath it.

The corpus point from the section above recurs in a sharper form. The offender
sample was never missing here: 728 stale citations were sitting in the deck the
whole time, and every pass walked past them and reported the category clean. A
check whose population contains hundreds of known offenders and which returns
none should have to say so out loud.

No `advances` edge, for the same reason given in the two notes above: that card
is an evidence connection on an open decision. It carries its own fix for the
citation check; this section carries only what it teaches about scope.

## Decision required

The technique is settled — a test that runs the scanner over synthetic source
carrying a known offender and asserts it is reported. `test_plugin_mirror_parity.py`
and `test_count_message_pluralization.py` both already do it. What needs a human
pick is **how the repo guarantees it**, and the two options differ in whether
they prevent recurrence:

- **A — per-guard sensitivity tests.** Add one `*_is_detected` case beside each
  of the four scanners, mirroring the existing precedent. Smallest diff, no new
  abstraction, matches how the two correct guards are already written. But it is
  opt-in per guard: the fifth prohibition guard someone writes next month is
  unprotected again, and this card's shape recurs — the same trap the sibling
  root cards `doc-accuracy-guards-are-opt-in-per-claim-…`,
  `draft-gating-is-opt-in-per-surface-…` and
  `query-flag-validation-is-opt-in-per-flag-…` all describe.

- **B — a shared harness that makes sensitivity structural.** Guards register
  `(scanner, known-offender-sample)` pairs with a common helper that generates
  both the prohibition assertion and its sensitivity case, plus a meta-test that
  fails when a prohibition scanner exists with no registered sample. Prevents
  recurrence rather than patching four instances; costs a new abstraction and a
  rewrite of guards that currently read as plain, obvious unittest code.

Option B is the shape this repo has reached for before when a family kept
respawning per-site fixes (see `unguarded-loader-callsites-keep-spawning-non-dict-shape-guard-fixes`
and `bare-string-scalars-on-list-fields-keep-spawning-per-consumer-guard-fixes`,
both of which frame the same per-site-versus-at-the-source choice). It is
also the heavier one, and with only four instances the threshold argument cuts
both ways. Whether four is past the line is the call to make.

A secondary question rides along: whether `reproduce.py`'s mutation harness
should itself become a CI test — "kill each prohibition scanner, assert the
suite goes red" is a stronger and more general guarantee than any per-guard
sample, and it needs no registration, but it multiplies suite runtime by the
number of prohibition guards.

## Fix

Deferred to the decision above. Do not start with the four patches: if B is
picked, those patches are thrown away.

**An Option-A-shaped scanner landed voluntarily (2026-08-03).** The successor
to the tautology described above shipped `tests/test_canonical_tag_rows.py`,
which scores the live deck against every `state` tag row and carries an
`OFFENDERS` table — one violating card per row, asserted rejected — beside the
clean-tree assertion. That is Option A's shape applied to a new scanner at
birth rather than retrofitted, and it cost roughly fifteen lines, which is a
data point for the per-scanner cost estimate the options need. It does **not**
narrow the scope question this section raises: the guard lives in `tests/`, so
it is inside both options already. The one-shot closure sweep — the surface
that produced the tautology — remains unreached by anything in the repo.
