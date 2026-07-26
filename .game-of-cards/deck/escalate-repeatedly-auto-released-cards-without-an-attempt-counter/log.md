## 2026-07-26: filed as the split-out backstop half

Split out of
[`autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish`](../autonomous-picker-wastes-passes-on-cards-only-a-human-can-finish/)
when that card's A/B/C/D decision resolved. The parent keeps the
prevention half (publish-time warning plus a `goc validate` lint keyed on
a shared `dod_is_human_only` predicate); this card takes the containment
half.

Split rather than bundled for two reasons. The prevention half is a
single predicate at two call sites with no schema change and no new
authority — cheap, and it should not wait. This half grants the engine
authority to mutate `human_gate` on its own, which no engine code does
today, so it needs its own DoD and its own regression coverage.

Filed at `human_gate: none` because the mechanism is fully decided, not
open: the two-rung ladder and the explicit rejection of an attempt
counter are recorded on the parent and restated in this card's README so
an implementer can act cold. The counter question is the one thing a
future reader is most likely to re-open — both rejected designs (a
frontmatter integer, and counting `## ` headings in `log.md`) are written
up with their specific failure modes rather than merely dismissed.

No value-flow edge to the parent. Neither card blocks the other; they
address one symptom through independent mechanisms, so an `advances` edge
would assert an ordering that does not exist.

## 2026-07-26: returned to draft same day — trigger defect found

Published, then returned to `draft: true` within the hour. The parent's
decision that spawned this card was rewound after
[`human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property`](../human-gate-is-card-level-but-human-only-ness-is-a-dod-item-property/)
was read — a card filed the same morning that carries `advances:` the
parent and disputes its premise.

The defect is in this card's escalation *trigger*, not its counter
analysis. The ladder fires on "released without closing," which treats a
pass that ticked three boxes identically to a pass that did nothing. That
card's evidence: a downstream card with eight DoD items, exactly one
human-only. The ladder as specified would have parked it on the second
release while seven items were still agent-workable — the failure it is
supposed to prevent, inverted.

What still stands: the rejection of both counter designs (a frontmatter
integer as machine-only telemetry with commit churn; `## ` heading counts
as a metric of deliberation rather than failure), and the observation
that the self-clearing `waiting_until` overlay can encode escalation
state without new schema. What must change before publishing: the trigger
must key on *absence of progress* (no box ticked, no commit landed), not
on release, and the rung must reset when progress happens.

Kept as a draft rather than closed — the analysis is worth preserving and
the card may still be the right home for the backstop once the
prerequisite's model is chosen. If that card adopts per-item gating, this
one may close as superseded instead.
