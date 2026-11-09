

## 2026-07-13 — Deck hygiene pass

Refreshed defunct citation: the `workflow.closure_on_integration` knob doc moved from `kickoff/SKILL.md:287` to `kickoff/reference.md:72-74` when the skill was split into core + reference (commit 8a1af2f5). Mechanical cite update (README + DoD item); claims unchanged.

## 2026-11-09T02:00:07Z — Staleness re-check

As-filed anchors gone from HEAD: `goc/templates/skills/kickoff/SKILL.md:287`
(`` - `workflow.closure_on_integration: true` — `goc done` refuses to close ``),
moved by `8a1af2f5`; `goc/engine.py:3601`
(`_enforce_no_inbound_superseded_by_or_exit(title, "done")`), deleted by `4ec2606c`.
Reproducer: `reproduce.py` → exit 1, "_cmd_status: integration check = False <-- DEFECT".
Verdict: still live. No rewrite for the kickoff cite: its 2026-07-13 token
`kickoff/reference.md:72-74` already matches HEAD.
Not placed: `# goc/engine.py:3601-3603` — its first endpoint (that guard call) is
gone, so the block has no two-ended home; the bundle loop is now `:5632-5633`
(integration check only). The README excerpts still quote the removed guard.
Gate unchanged.
