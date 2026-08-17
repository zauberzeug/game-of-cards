## 2026-07-26 — filed from a downstream instance, and it corrects a sibling card

Filed while unblocking the zoe-app deck. Rodja asked why the attachments
card was parked at `human_gate: session` when everything except the final
live check was ordinary agent work — "it should be auto first, and only
switch back to session once it is otherwise finished."

Reconstructing the card's history showed the gate was **right when it was
set** (2026-07-20: the three then-blocking DoD items were live-gateway
discovery) and became **wrong three days later** (2026-07-23: those boxes
were ticked by an attended session). Nothing re-evaluated it, because
nothing had recorded what it was for. The gate was raised by a downstream
wrapper's release-attempt counter via a `sed` on the frontmatter, and the
reason went into `log.md` prose that no predicate reads.

Two further findings folded into the card body:

- The escalation deliberately left `status: active`, so the card carried
  two independent locks. Lowering the gate did not make it pullable; that
  needed a separate `goc status … open`. The `worker:` still named a
  drain worktree deleted six days earlier.
- `goc decide` lowers a gate; **no verb raises one**. Every consumer that
  needs to escalate hand-edits frontmatter, which is why the reason is
  never structured.

Also corrected the premise of
`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`, which
cited this same zoe-app card as its canonical *structurally human-only*
example. Eight DoD items, one human-only — it is a mixed card, and that
sibling's proposed lint ("any `EMPIRICAL:` item mentioning production or
a device ⇒ gate at `session`") would have made the observed failure
worse. Rewrote its "What's broken" parenthetical in place and cross-linked
both directions; wired `advances` so the two resolve together.

Left at `human_gate: decision`: four models are on the table (gate closure
rather than the pull, per-item gating, fix only the counter, or split
cards by convention) and picking among them changes the schema, so it is
not an agent's call.

## 2026-08-17 — in-repo instance: the shipped Andon cord itself hand-edits frontmatter

A `Skill(pull-card)` session on
`deck-fills-with-decision-gated-cards-faster-than-they-are-decided` hit the
"no verb raises a gate" finding recorded above, in this repo rather than
downstream. The card needed a human pick, so the skill's own documented
escalation applied — "raise the gate to `decision` or `session`, write a
`## Decision required` body section, commit the gate-and-body update" — and
there is no CLI for the first clause. The agent edited
`human_gate: none` to `human_gate: decision` directly in the YAML, then ran
`goc status … open` separately, so the park took two mutations and one
hand-edit where `goc decide` does the mirror-image lowering in one verb.

The datapoint this adds: the gap is not only a downstream-wrapper problem
solved by `sed`. It is reached by following goc's own shipped skill text on
its own deck, which means every consumer running the Andon cord as
documented hand-edits frontmatter, and the reason for the gate lands only in
prose. That strengthens DoD item 3 — a raising verb symmetric to
`goc decide` — and is evidence from the default path rather than from a
wrapper.

Recorded as a cross-reference, not a new card: this card already names the
shape, per the dedup-then-connect rule.
