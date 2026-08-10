
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
