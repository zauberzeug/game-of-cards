## 2026-05-24: literature deep-research pass

Ran a four-track literature review (parallel research agents) and rewrote the
README body from a thin prior-art list into a literature-grounded design doc.

Tracks: (1) Lean/Kanban/TOC practice, (2) formal state/workflow modelling
(Harel statecharts, Workflow Patterns, Petri nets), (3) tool survey (Jira,
Linear, Asana, GitLab, GitHub, Azure DevOps, Shortcut, OmniFocus, Things,
Todoist, GTD), (4) project-scheduling + bug-lifecycle theory (CPM/PDM, Bugzilla).

Key cross-track convergence:
- `blocked`-as-status is rejected by all four bodies (Harel state-explosion;
  Kanban "thou shalt not have a blocked status"; every mature tool uses a
  flag/badge/relation overlay; CPM/Petri compute readiness rather than store it).
- Dependency-blocking should be DERIVED from the graph (it un-blocks itself);
  GoC's `STALE_BLOCKED` is a half-built guard that only warns.
- Only exogenous waits (external/resource/time) need a STORED overlay with a
  typed reason + optional date. GoC already owns decision-wait (`human_gate`)
  and rejection (`disproved`/`superseded`).
- Secondary: the single `advances` edge is Finish-to-Start only (PDM has
  FS/SS/FF/SF + lead/lag); Kanban gives an aging/SLE escalation path
  (waiting → blocked when the expected date elapses).

Proposed model recorded in README: three orthogonal axes — progress status,
derived dependency readiness, stored impediment overlay. Decision still parked
(gate: session); the open questions are listed at the foot of the README.
Sources captured in the README "Sources" section.

## 2026-05-24: decision recorded — full decomposition; promoted to epic

Design session chose **full decomposition** over hybrid-redefine and
minimal-annotate. Decision: remove `blocked` from the status enum; derive
dependency-readiness from the `advances` graph (self-clearing); add a stored
`waiting_on` {external|resource|deferred} + optional `waiting_until` impediment
overlay evaluated as a read-time guard; extend the ready-to-pull predicate.
`human_gate` (decision-wait) and `disproved`/`superseded` (rejection) unchanged.
FS/SS/FF/SF edge typing explicitly deferred. Gate session → none. Card retagged
`epic`.

Why: all four literature tracks converge on blocked-as-orthogonal-overlay +
derived dependency-readiness; GoC already owns decision-wait (`human_gate`) and
rejection (`disproved`/`superseded`); full decomposition is the most expressive
(a card may be `active` AND impeded) and the breaking migration is acceptable
before the audience widens.

Deliberation archived: the three model options and their trade-offs are recorded
in the README "## Decision" section; the rejected alternatives were
hybrid-redefine-blocked (keep the status, less breaking, small impurity) and
minimal-annotate (cheapest, does not fix the anti-pattern).

Children filed: `derive-dependency-readiness-instead-of-storing-blocked-status`,
`add-waiting-overlay-with-reason-and-until-date`,
`remove-blocked-from-status-enum-and-migrate-existing-cards` (the last
advanced_by the first two; breaking, lands last).
