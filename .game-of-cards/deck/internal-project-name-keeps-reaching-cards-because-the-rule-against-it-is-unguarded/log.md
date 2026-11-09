## 2026-11-09T02:35:38Z — Filed from the refine-deck pass's pattern check

The pass's Stop-hook pattern check asked whether its changes touched a
broader pattern. Answering it meant sweeping the deck's live cards for
identifiers that do not exist. The sweep found 10 names that never existed in
code history; 8 are proposed helpers, which is legitimate. One card named a
downstream consumer by the internal project name AGENTS.md forbids. A full
search then found 16 such lines across 6 cards, three of them older than the
2026-07-27 "audited clean" sentence.

Dedup: the only card on the rule is the closed
`card-authoring-rules-in-agents-md-have-no-enforcement-path`, whose scope decision rested on there being no instance. Per
"closure is not frozenness", this is post-close evidence: a new card, plus a
forward pointer on the closed one.

Filed at `human_gate: none`. Redacting the lines and correcting the AGENTS.md
sentence are mechanical. The guard recommendation revisits that card's
decision with evidence it did not have; a reader who disagrees can raise the
gate. This card names neither the project nor the individual; § Instances
gives card titles and line numbers.
