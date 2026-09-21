
## 2026-07-29T06:02:00Z — Sibling property connected from a closed instance

`card-language-guard-flags-legitimate-english-as-non-english` closed today and
the Stop-hook pattern check routed it here. Body gains § "Sibling property:
sensitivity is necessary but not sufficient".

It is this card's own compliance case turned counter-example.
`tests/test_card_authoring_rules.py` cites this card by title in its module
docstring and carries `RECALL_CASES` as the demonstration this card asks for —
and `scripts/check_card_language.py` still shipped a false-positive defect that
rejected 9 of 26 English `-ung` words plus the DES cipher acronym. Every recall
case passed throughout, and had to: a sensitivity case asserts the scanner
fires, which is what a false positive also is.

Bearing on the pending decision: Option B's `(scanner, known-offender-sample)`
registration is one-sided, and wants a third element — a known-clean near-miss.
The near-miss has to be absent from the current corpus to be worth anything; the
closed card's predecessor swept 4,363 live deck tokens for matches and found
none, a real measurement against the wrong population. No status or gate change
here — this is supporting evidence on an open decision card, and the decision
now covers both directions rather than needing a fifth umbrella.

## 2026-08-02T05:58:00Z — Third counter-example, and a live false negative

Connected [schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen](../schema-parity-guard-enumerates-keys-so-new-keys-drift-unseen/)
(closed today) as a third in-tree instance of the sensitivity-control
technique. Body rewritten in place: "Two guards … are the counter-examples"
→ three.

Not a member of the offender family, and deliberately not an `advances` edge.
`test_skill_schema_yaml_parity` is fail-closed by this card's own taxonomy —
`assertEqual(engine, skill)` cannot pass on a dead read — so it belongs with
`test_plugin_mirror_parity.py` and `test_count_message_pluralization.py` as a
counter-example, not in the table of four fail-open scanners.

What it adds to the open decision: the controls caught a **real** false
negative, not a hypothetical one. That probe's first draft reported all four
cases as caught and would have disproved its own card; the guard under test
builds its failure message with `relative_to(ROOT)` eagerly, on passing calls
too, so redirecting the schema paths without rebinding `ROOT` made every test
error on message construction rather than run. Two passing states, one green
result — this card's thesis, hit in the harness instead of the scanner.

The sharp edge for whatever scope gets picked: that is the same copy-and-rebind
mechanism this card's own `reproduce.py` uses. So the baseline/control line is
not optional rigour to be trimmed when the fix is applied at scale — it is the
only thing that distinguishes "nothing drifted" from "nothing ran".

No status or gate change; the decision stays open.

## 2026-08-03T03:20:00Z — Fourth surface: a closure verification that could not fail

A refine-deck pass refuted the closing figure of
`meta-fix-tag-predicate-mismatches-how-the-deck-applies-the-tag` and routed
the shape here. Body gains § "A fourth surface: closure verifications, which
no option below reaches".

The mechanism is this card's thesis in a place neither option covers. That
card's `EMPIRICAL:` DoD box was discharged by a sweep over "per-card README
read" — the whole file, frontmatter included — testing whether the literal
`meta-fix` appears in the title, `summary:` or body. Every `meta-fix`-tagged
card carries that literal in its own `tags:` line, so the check held for all
45 cards by construction. Replayed at the same commit against the engine's
`card.body`, 5 of the 45 fail.

Two things worth carrying into the scope decision. First, the diagnostic was
already in the recorded output: the reported pass count was exactly the
population size, which is the signature of an assertion with nothing to
distinguish. Second, this surface is not in `tests/` and never will be — a
card's verification script runs once, is quoted into a closure note, and is
never executed again — yet its output becomes the record other cards reason
from. Here it was cited as settled for 26 days.

So the offender table's boundary is a scope question, not just a scale one.
Option A and Option B both attach to committed scanners; neither reaches a
one-shot closure sweep. Recorded as evidence, not as a fifth umbrella — the
mechanism question is still the same one this card already asks.

No status or gate change; no edge, per the same reasoning as the
schema-parity connection. The decision stays open.

## 2026-08-10 — Fifth surface connected

The 2026-08-10 deck hygiene pass surfaced a fail-open check outside `tests/`
and outside card-directory scripts: `refine-deck`'s defunct-citation category,
specified in prose as "the cited line is ≤ EOF" at
`goc/templates/skills/refine-deck/SKILL.md:105`.

Measured recall over this deck: 0 of 482 moved citations reported, while the
check called all 706 citations clean. Unlike the four scanners in the table,
this one has no dead-scanner story — the predicate never had non-zero recall on
the rot it names, because a bounds test can only fire when a file shrinks past
the cite and source files grow.

Recorded as "## A fifth surface" in the README because it constrains the scope
question rather than the technique: both options attach to a Python callable,
and a prose-specified check has none to register. Cross-reference only, no
`advances` edge — consistent with the schema-parity and closure-verification
connections already on this card. The instance carries its own fix in
`refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file`.

## 2026-09-07T05:06:00Z — Sixth surface: the technique applied voluntarily to a new guard

`citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range`
closed in `a990a849` and cited this card in its DoD, so the new guard was
built with controls from the start rather than retrofitted. Two of them, on
the two halves of a prose-plus-fixture guard:

- the prose classifier `documented_range_coherence` is fed the exact sentence
  the fix replaced and asserted to return `PAIR_UNCHECKED`, so it is shown
  producing the failing verdict and not only the passing one;
- the repo fixture is run with the pair check switched off and asserted to
  write the inverted range `10-8`, so a fixture that stopped reproducing the
  divergence could not read as "the recipe declines correctly".

Confirmed end to end: reverting the shipped `SKILL.md` step 1 to its pre-fix
sentence turns three of the new tests red, and restoring it turns them green.

A datapoint for the scope question this card is parked on. It cost roughly
two extra assertions on a guard being written anyway, and it caught nothing —
which is the expected outcome on a guard authored the same hour, and is why
the cost of the technique is better measured here than on the retrofit cases.
The four guards in this card's offender table are still unaddressed; nothing
about this closure narrows them.

## 2026-09-21T05:20:00Z — Seventh surface, and the two-failing-states mirror

Connected from
[contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions](../contributor-guide-sends-readers-to-a-conventions-file-that-holds-no-conventions/)
(closed 2026-09-21, commit `d79a7531`). The new
`ContributorGuideAccuracyTest` lands in `tests/test_guidance_accuracy.py` —
the file that holds three of the four guards in this card's offender table —
and was written with sensitivity proof from the start, so the two shapes now
sit side by side in one module for anyone weighing the scope question.

Two controls, because the seven checks needed both directions:

- **historical fixture** — the pre-fix `CONTRIBUTING.md` clauses, verbatim
  under their real headings, fed to the same `_contributing_findings(text)`
  the passing assertion calls. The test asserts *every* check id fires, not
  that some list is non-empty, so one check going quiet is a failure rather
  than a quieter pass.
- **per-check mutation isolation** — each of the seven claims reintroduced
  alone into the repaired file, asserting exactly that check fires and no
  other. The fixture alone would not have caught a check that fires for the
  wrong reason: three of `mirror-refresh-mechanism`'s clauses trip together
  on the historical text.

Taking the text as an argument rather than reading the file is what made both
possible, and it cost nothing — the passing assertion reads the file and
hands it over.

**The new datum is the inverse failure.** This card's third entry recorded
controls catching a check with two *passing* states (nothing drifted vs
nothing ran). The card above hit the mirror: its filed `reproduce.py` graded
the quote convention as `if double > single` — measured from the tree alone,
never reading what the guide claimed — so it had two *failing* states, "the
guide is wrong" and "the guide is right but the check never looked". It could
not go green, and the DoD it was written for says it must. Three sibling
checks in the same script were pinned to one day's wording the same way.

That shape is invisible to everything this card proposes: a known-caught
control confirms it fires, which it does, always. Only running it against the
repaired surface distinguishes them — which for a card artifact means the
closing session, the one session with an interest in the check being
satisfiable. Whatever scope is picked, an artifact whose DoD promises it will
exit zero is worth a *green* control as much as a red one.

No decision recorded — the gate stays `decision`; the four guards in the
offender table are still unaddressed.

## 2026-09-21T05:55:00Z — Eighth surface: an execution guard, which can assert its own coverage

Connected from
[shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids](../shipped-epic-recipe-builds-the-backwards-edge-its-own-next-bullet-forbids/)
(closed 2026-09-21, commit `b1b7ad8f`). The new
`SkillAdvanceExampleDirectionTest`
(`tests/test_skill_advance_example_direction.py`) walks every
`goc advance A --by B` occurrence in all six shipped skill trees, pairs it
with the `<role>.advances: [<role>]` encoding claim stated in the same
markdown block, and runs it against a scratch deck — the defect it pins was a
recipe whose stated encoding and given verb were both plausible English and
disagreed only once something executed them.

Written with sensitivity proof from the start, so this is a compliance datum
rather than a retrofit. Two controls, and the second is a shape this card has
not recorded:

- **historical fixture** — the pre-fix aggregation-epic bullet verbatim, fed
  to the same `_examples_in(text, source)` the passing assertion calls, with
  the guard required to both read a claim out of it and reject the example.
- **direct coverage assertion** — `test_the_covered_set_is_not_empty` reads
  the scan result itself and fails if no example is paired with a claim,
  reporting the example sites it saw but could not cover.

The second control is available because the guard's assertion is an
*execution*, not a scan: the scan is an intermediate value the test can
inspect, where a prohibition guard's scan and assertion are the same
expression. So the two-passing-states problem splits. A dead scanner still
passes silently and still needs the fixture — but "nothing ran" is directly
assertable, with no historical text to keep, and it degrades usefully: an
author who deletes an encoding claim while editing a skill body is told which
example sites went uncovered rather than watching the guard go quiet.

Cheap enough to be non-optional. The four guards in this card's offender table
each scan into a list before asserting it empty, so each could assert what it
scanned in one more line — which narrows the cost objection under
`## Decision required`, though it does not answer the scope question. Nothing
about this entry addresses those four; they remain unaddressed, and the gate
stays `decision`.

