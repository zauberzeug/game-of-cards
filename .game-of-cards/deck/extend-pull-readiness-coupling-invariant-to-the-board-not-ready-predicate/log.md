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
