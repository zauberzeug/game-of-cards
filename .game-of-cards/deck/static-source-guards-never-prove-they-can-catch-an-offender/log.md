
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
