---
title: blocked-status-conflates-dependency-external-wait-and-deferral
summary: "`status: blocked` is one generic state covering distinct situations with different resolution mechanisms. Four independent literature bodies (formal statecharts, Lean/Kanban, tool practice, scheduling/Petri theory) converge: blocked should not be a sequential status — dependency-blocking is derived from the graph, and only exogenous waits (external/resource/time) need a stored overlay with a typed reason + optional date. Design pass needed to choose the GoC shape."
status: open
stage: null
contribution: medium
created: "2026-05-24T04:32:39Z"
closed_at: null
human_gate: session
advances: []
advanced_by: []
tags: [api-contract, documentation]
definition_of_done: |
  - [ ] Design decision recorded: is `blocked` removed from the status enum in favour of (progress status) + (derived dependency readiness) + (stored impediment overlay), or a lighter variant? Decide stored-vs-derived-vs-overlay per subtype.
  - [ ] Decision on card-dependency blocking: upgrade `STALE_BLOCKED` from warn-only to a derived/computed readiness state (un-blocks itself when the last prereq closes), or keep it advisory.
  - [ ] Decision on the genuinely-missing case: typed wait/defer overlay with optional until/expected date (external delivery, resource/person, postpone), including whether it auto-resurfaces and whether an elapsed date escalates waiting → blocked (Kanban SLE pattern).
  - [ ] Relationship to existing mechanisms clarified: human-decision-wait is already `human_gate`; rejection is already `disproved`/`superseded`. The spec must state how the new overlay composes with these and with the `pull-card` loop-safety filter.
  - [ ] Decision on dependency-edge expressiveness: is the single FS-style `advances` edge kept, or is dependency *type* (FS/SS/FF/SF) and/or lead/lag in scope? (Likely out of scope, but the model must not assume FS == dependency.)
  - [ ] If new schema fields result: schema.yaml + card-schema skill + emitter + `goc validate` coverage; if behavior-only: engine + skills updated. Either way the advance-card skill's blocked guidance is rewritten to match.
---

# `blocked` is one generic status where the literature uses several distinct mechanisms

GoC models "stuck" as a single `status: blocked`. A four-track literature
review (see Sources) shows "blocked" decomposes into several situations with
*different resolution mechanisms* — and that GoC has already, in two places,
solved this correctly (`human_gate` for decision-waits, `disproved`/`superseded`
for rejection). The remaining gap is real.

## Headline: four independent disciplines reach the same verdict

| Discipline | Verdict on `blocked`-as-status |
|---|---|
| **Formal state modelling** (Harel statecharts) | State-explosion anti-pattern. "Blocked" is an *orthogonal region*; a card can be `active` **and** `blocked` simultaneously. Collapsing it into the progress enum forces a cartesian blow-up of states. |
| **Lean / Kanban** (D. J. Anderson) | "Thou shalt not have a blocked status." Keep the card in its workflow column and *flag* it; a status move loses workflow position and removes the WIP-limit pressure that forces resolution. |
| **Tool practice** (survey of 10+ tools) | Every mature tool separates the impediment *signal* (flag/badge/relation) from the workflow *status*: Jira flag, Linear orange badge, GitLab board badge, Azure DevOps "Impediment" work-item. None makes blocked a peer of in-progress/done. |
| **Scheduling & workflow theory** (CPM, Petri nets, Workflow Patterns) | "Cannot proceed yet" is **derived** — computed from predecessor completion (CPM forward/backward pass) or from token marking (Petri transition-enabling). The Milestone pattern models it as a *guard on a transition*, not a stored flag. |

The single strongest cross-track signal is **derived vs. stored**: a guard
auto-clears when its condition clears; a stored status strands the card when
the blocker resolves silently. GoC's `validate_blocker_coherence`
(`engine.py:1118`) already walks `advanced_by` as the blocker set
(`engine.py:1153`) — but only **warns** (`STALE_BLOCKED`) instead of deriving
the state. It is a half-built guard.

## The decomposition the literature points to

Replace the single `blocked` status with three orthogonal axes:

1. **Progress** (sequential status): `open → active → done/disproved/superseded`.
   `blocked` is **removed** from this enum.
2. **Dependency readiness** (DERIVED, never stored): computed from `advanced_by`
   + predecessor status. A card is dependency-blocked iff it has a non-terminal
   prereq, and it un-blocks itself when the last prereq closes. This is the
   upgrade of `STALE_BLOCKED` from warn → computed state.
3. **Impediment overlay** (the ONLY stored part): an orthogonal flag carrying a
   **typed reason** + an **optional until/expected date**. This is the sole
   case the graph cannot derive — exogenous waits.

### Subtype map (GoC already owns two of five)

| Block kind | Literature model | GoC verdict |
|---|---|---|
| **Dependency** (upstream card must finish) | CPM "early start" derived; Petri precondition; Bugzilla `depends_on` graph (does *not* auto-set a status) | derive from the `advances` graph; **no field** |
| **External / resource wait** (vendor, hardware delivery, a specific person) | Azure "Impediment" item; GTD "Waiting For" list; GitLab scoped label | **the missing piece**: stored overlay + reason; exogenous, cannot be derived |
| **Time-based deferral** (postpone) | MS Project "Start No Earlier Than"; OmniFocus *defer date*; Things "When"; GTD *tickler* | overlay + `until` date that **auto-resurfaces** |
| **Human decision** (choose/approve) | — | **already `human_gate: decision/session`** ✓ |
| **Rejected** (won't do) | Bugzilla WONTFIX (terminal) vs DEFERRED (still to-do) | **already `disproved`/`superseded`** ✓ |

`human_gate` is the proof-of-pattern: GoC already models one block-kind
(decision-wait) as a typed first-class mechanism rather than a generic status.

## Two secondary findings

- **The single edge is Finish-to-Start only.** Precedence theory (PDM) has four
  dependency types — FS (what `advances` is), Start-to-Start, Finish-to-Finish,
  Start-to-Finish — plus **lead/lag** as *edge* metadata. The one edge cannot
  express "B starts when A starts" or "B can't finish before A." Probably out of
  scope, but the model must not assume FS == dependency.
- **Aging/escalation lifecycle (Kanban).** A *waiting* item carries an expected
  date (SLE); when the date elapses it **escalates to blocked** (andon). This
  gives "postpone" and "external wait" an aging path instead of sitting silently
  forever. *Class of service* (urgency) is a **separate orthogonal axis** from
  block-reason; a complete model tracks both. WIP-limit treatment differs too:
  blocked items stay in-column and keep consuming WIP (the pressure that forces
  resolution); parking-lot waits get a separate limit.

## The three motivating questions, now answered by the literature

1. **Walk `advances` upstream to find blockers?** Yes for card-blocks-card —
   this is the CPM/Petri/Asana/GitLab model, and GoC already walks it. But the
   graph is structurally blind to non-card blockers (delivery, person, time):
   no upstream card exists to walk to.
2. **How does a blocked card discover it is unblocked?** Make dependency-block
   *derived* and it discovers itself (the guard clears). Stored `blocked` is the
   Jira problem (no native auto-transition; cards get stranded).
3. **Is `blocked` too generic?** Unanimously yes. Each kind resolves by a
   different mechanism, so one status cannot carry the resolution signal.

## Open questions for the design session

- Remove `blocked` from the status enum entirely (→ derived readiness + a
  `waiting`/`on_hold` overlay), or keep it as an umbrella with a typed reason
  sub-field? (Schema-migration cost vs. cleanliness.)
- Does an until-date get an active resurface/escalation hook (scheduler, or
  surfaced by standup/`goc validate`), or is it advisory only?
- How does the overlay compose with `human_gate` and the `pull-card`
  loop-safety filter (`human_gate: none`)?
- Is dependency-edge typing (FS/SS/FF/SF, lead/lag) in scope now, or deferred?

## Sources

**Lean / Kanban / TOC**
- djaa.com — [WIP limits for blocked vs waiting items](https://djaa.com/kanban-evergreen-should-we-include-waiting-or-blocked-items-in-wip-limits/)
- nkdagility — [Blocked columns obfuscate workflow](https://nkdagility.com/resources/blog/blocked-columns-on-kanban-boards-obfuscate-workflow-and-undermine-effectiveness/)
- LEANability — [Blocker clustering in practice](https://www.leanability.com/en/blog/2017/05/blocker-clustering-in-practice/)
- Businessmap — [Block clustering](https://businessmap.io/kanban-resources/kanban-analytics/block-clustering)
- Kanban Tool — [Classes of Service](https://kanbantool.com/kanban-guide/classes-of-service)
- Nave — [Managing blocked work in Kanban](https://getnave.com/blog/blocked-work-in-kanban/)

**Formal state / workflow modelling**
- Harel — [Statecharts: A Visual Formalism for Complex Systems (1987)](https://www.sciencedirect.com/science/article/pii/0167642387900359)
- statecharts.dev — [State machine state explosion](https://statecharts.dev/state-machine-state-explosion.html) · [Parallel (orthogonal) state](https://statecharts.dev/glossary/parallel-state.html) · [Guard](https://statecharts.dev/glossary/guard.html)
- Workflow Patterns — [Milestone (WCP18)](http://www.workflowpatterns.com/patterns/control/state/wcp18.php) · [Deferred Choice (WCP16)](http://www.workflowpatterns.com/patterns/control/state/wcp16.php)
- van der Aalst — [The Application of Petri Nets to Workflow Management](https://users.cs.northwestern.edu/~robby/courses/395-495-2017-winter/Van%20Der%20Aalst%201998%20The%20Application%20of%20Petri%20Nets%20to%20Workflow%20Management.pdf)

**Tool survey**
- Jira — [Thou shalt not have a "blocked" status](https://medium.com/the-pinch/thou-shalt-not-have-a-blocked-status-in-jira-9bcafde684b8) · [Flag feature](https://community.atlassian.com/forums/Jira-articles/Why-flagging-Jira-issues-is-so-cool/ba-p/1872469)
- Linear — [Issue relations](https://linear.app/docs/issue-relations) · [Triage / snooze](https://linear.app/docs/triage)
- Asana — [Dependencies](https://help.asana.com/hc/en-us/articles/23567568831899-Use-dependencies-to-kick-work-off-at-the-right-time)
- GitLab — [Related/blocking issues](https://docs.gitlab.com/ee/user/project/issues/related_issues.html) · [Scoped labels](https://university.gitlab.com/courses/scoped-labels)
- GitHub — [Issue dependencies (GA 2025)](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/creating-issue-dependencies)
- Azure DevOps — [Manage issues/impediments](https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/manage-issues-impediments?view=azure-devops)
- OmniFocus — [GTD and the power of Defer](https://www.arkusinc.com/archive/2020/gtd-and-the-power-of-defer-in-omnifocus)
- GTD — [Tickler system](https://www.shortform.com/blog/tickler-system-getting-things-done/)

**Scheduling & issue-lifecycle**
- PDM — [Four dependency types FS/SS/FF/SF](https://www.mypminterview.com/p/explain-dependency-types-fs-ss-ff-sf)
- [Lead vs lag time](https://pmstudycircle.com/lead-vs-lag/)
- MS Project — [Start No Earlier Than constraints](https://tensix.com/microsoft-project-2013-start-no-earlier-than-constraints/)
- Bugzilla — [Understanding a bug (depends_on/blocks, resolutions)](https://bugzilla.readthedocs.io/en/latest/using/understanding.html)
- [Eclipse Bugzilla — LATER/REMIND deprecation](https://bugs.eclipse.org/bugs/show_bug.cgi?id=178923)
