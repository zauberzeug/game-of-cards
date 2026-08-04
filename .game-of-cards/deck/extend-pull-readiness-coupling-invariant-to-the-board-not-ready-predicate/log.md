## 2026-06-18T05:35:00Z — Additional drift instance found

A fourth hand-rolled liveness gate surfaced and was fixed in
[`verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards`](../verbose-table-shows-awaiting-prereq-line-on-terminal-status-cards/):
`render_table`'s verbose `awaiting: <prereq> (you may start)` advisory
(`engine.py:2677`) computed `dependency_blockers` for terminal cards too,
because it lacked the board's `live = t.status not in TERMINAL_STATUSES`
guard. It was patched in place by mirroring the board, but — like copy #3
(the board itself) before this card — it is **not** covered by any coupling
guard, so it can drift again. When the shared rejection-axis helper / coupling
test from this card's `## Decision required` is implemented, include the table
renderer's advisory gate as a fourth covered site (the relevant axis there is
`status ∈ TERMINAL_STATUSES`, the liveness clause, not the full pull-readiness
cross-product).

## 2026-07-23 — fourth copy confirmed (audit)

An audit pass confirmed a fourth hand-rolled pull-readiness copy, in
shell outside the engine: `.github/workflows/pull-card.yml` gates its
agent-launch and self-retrigger steps on
`goc --status open --human-gate none --json | jq length`, omitting the
waiting-overlay axis. Filed as
`pull-card-workflow-launches-agent-sessions-when-the-ready-queue-is-empty`
(contribution: high — live false launches on this repo's own deck:
workflow predicate counts 3, `--ready` counts 0). Body's "What's
broken" rewritten in place to record the fourth copy.

## 2026-08-04 — fifth copy confirmed, and it constrains the decision (audit)

A fifth hand-rolled restatement of the pull-readiness predicate was
confirmed, this one in **prose rather than code**:
`render_empty_query_line` renders the ready predicate as the sentence
`"ready: status open, gate none, no active impediment"`, which names three
of `card_is_ready`'s four conjuncts and omits the `card_is_draft`
exclusion. It has therefore already drifted — a scratch deck holding one
`status: open` / `human_gate: none` / unimpeded / `draft: true` card
prints that sentence while `--status all` shows the card, so every
condition the message names holds and the card is still excluded.

Surfaced while working
`empty-result-line-reports-a-drained-ready-queue-that-still-has-cards`
(a separate defect in the same sentence: `--ready` suppressed an explicit
`--status` from the enumeration). Recorded here as evidence rather than
filed as its own card — it is an instance of this card's catalogued
pattern, and filing a sixth umbrella would be the redundant-root
anti-pattern.

The reason it matters beyond incrementing a count: it discriminates
between the two options in `## Decision required`. Option (b) — extend
`test_scheduler_workable_predicate_coupling.py` to introspect additional
predicates — is structurally unable to cover a prose string, so under (b)
this fifth copy stays unguarded and keeps drifting. Option (a) can cover
it, but only if the extracted helper surfaces the rejection axes as
*named labels* the message can render, not just a boolean or an opaque
set. Body's "What's broken" rewritten in place to record the fifth copy
and that requirement on (a)'s shape.
