
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
