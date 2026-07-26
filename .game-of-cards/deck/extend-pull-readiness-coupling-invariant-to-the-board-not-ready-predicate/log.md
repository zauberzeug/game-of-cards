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
