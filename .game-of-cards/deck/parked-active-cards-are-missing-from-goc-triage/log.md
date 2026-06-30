## 2026-06-30 — Related fix: second divergence of the same hand-rolled triage filter

A sibling defect in the *same* `_cmd_triage` candidate filter was found
and fixed today: `goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards`
(closed). That filter omitted the `card_is_draft` exclusion every other
listing surface applies via `filter_cards`, so `draft: true` scaffolds
leaked into the triage view. Both bugs share one root cause — `_cmd_triage`
re-implements its candidate filter instead of routing through `filter_cards`.

Coordination note for whichever option (A/B/C) this card implements: the
filter now reads

```python
all_cards = [
    t for t in load_all_cards()
    if t.status == "open" and t.human_gate != "none" and not card_is_draft(t)
]
```

(`goc/engine.py` — the line drifted to ~5965 since this card's `4613`
reference). The `not card_is_draft(t)` clause MUST be preserved by the
chosen fix — Option A's snippet above drops the `status` clause but omits
`card_is_draft`, which would regress the draft fix. The durable form is to
route the whole candidate set through `filter_cards` (which already applies
the draft exclusion) rather than hand-rolling the comprehension a third time.
