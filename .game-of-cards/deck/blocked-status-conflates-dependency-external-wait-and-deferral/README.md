---
title: blocked-status-conflates-dependency-external-wait-and-deferral
summary: "EPIC. `status: blocked` conflates distinct situations. Decided (full decomposition): remove `blocked` from the status enum, derive dependency-readiness from the advances graph (self-clearing), and add a stored impediment overlay (`waiting_on` reason + optional `waiting_until` date) evaluated as a read-time guard. Delivered via three children."
status: open
stage: null
contribution: medium
created: "2026-05-24T04:32:39Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - derive-dependency-readiness-instead-of-storing-blocked-status
  - add-waiting-overlay-with-reason-and-until-date
  - remove-blocked-from-status-enum-and-migrate-existing-cards
  - no-guardrail-for-canonical-epic-edge-direction
  - advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose
  - make-advances-gate-closure-not-the-pull-queue
tags: [epic, api-contract, documentation]
definition_of_done: |
  - [x] Agreed design recorded in this body (done — see "## Decision").
  - [x] Child `derive-dependency-readiness-instead-of-storing-blocked-status` closed.
  - [x] Child `add-waiting-overlay-with-reason-and-until-date` closed.
  - [ ] Child `remove-blocked-from-status-enum-and-migrate-existing-cards` closed.
  - [x] AGENTS.md + card-schema/advance-card/deck skills describe the three-axis model (progress status / derived dependency readiness / stored impediment overlay).
worker: {who: "claude[bot]", where: main}
---

# `blocked` is one generic status where the literature uses several distinct mechanisms

GoC models "stuck" as a single `status: blocked`. A four-track literature
review (see Sources) shows "blocked" decomposes into several situations with
*different resolution mechanisms* — and that GoC has already, in two places,
solved this correctly (`human_gate` for decision-waits, `disproved`/`superseded`
for rejection). The remaining gap is real.

This card is the **epic**; the agreed design is recorded below and the
implementable work lives in three child cards.

## Decision — agreed design (2026-05-24, full decomposition)

Chosen in a design session over three alternatives (full decomposition /
hybrid-redefine-blocked / minimal-annotate). **Full decomposition** was chosen:
most literature-aligned, most expressive (a card may be `active` AND impeded),
and the breaking migration is acceptable before the audience widens.

1. **Progress status loses `blocked`** → `open → active → done/disproved/superseded`.
2. **Dependency readiness is DERIVED**, never stored: a card with any
   non-terminal `advanced_by` prereq is computed "blocked-by-dependency" and
   self-clears when the last prereq closes. Replaces the manual
   `status: blocked`-for-a-dependency pattern and the warn-only `STALE_BLOCKED`.
3. **Impediment overlay is the only STORED part**: `waiting_on` ∈
   {`external`, `resource`, `deferred`} plus an optional `waiting_until` ISO
   date. Evaluated as a **read-time guard** (no daemon): a future
   `waiting_until` makes the card not-ready (hidden from queues); an elapsed one
   is surfaced by `goc validate` / standup as an SLE-escalation signal. A card
   may be `status: active` AND carry `waiting_on`.
4. **Ready-to-pull predicate** (pull-card / next-card loop safety) becomes:
   `status == open AND human_gate == none AND no non-terminal advanced_by AND
   no active impediment (waiting_on unset, waiting_until absent or past)`.
5. **Unchanged:** `human_gate` already models decision-waits;
   `disproved`/`superseded` already model rejection. The overlay composes
   alongside them.
6. **Deferred (out of scope):** dependency-edge *typing* (FS/SS/FF/SF) and
   lead/lag. The single FS-style `advances` edge is retained; the model simply
   stops assuming FS == the only possible dependency.

## Delivery — child cards

| Child | Scope | Order |
|---|---|---|
| [derive-dependency-readiness-instead-of-storing-blocked-status](../derive-dependency-readiness-instead-of-storing-blocked-status/) | Compute dependency-block from `advanced_by` + predecessor status; self-clearing; repurpose `STALE_BLOCKED`/`ORPHAN_BLOCKED`; surface in `goc status`/board. | first |
| [add-waiting-overlay-with-reason-and-until-date](../add-waiting-overlay-with-reason-and-until-date/) | New `waiting_on` enum + optional `waiting_until` date in schema; emitter; `goc validate` rules; read-time guard + elapsed-wait surfacing; advance-card UX to set/clear. | first (parallel with above) |
| [remove-blocked-from-status-enum-and-migrate-existing-cards](../remove-blocked-from-status-enum-and-migrate-existing-cards/) | Drop `blocked` from `status_values`; migrate existing blocked cards (dependency → `open`+edges; exogenous → `open`+`waiting_on`); rewrite card-schema/advance-card/deck skills + AGENTS docs. **Breaking** — coordinate with a release boundary. | last (depends on both above) |

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

## Subtype map (GoC already owns two of five)

| Block kind | Literature model | GoC verdict |
|---|---|---|
| **Dependency** (upstream card must finish) | CPM "early start" derived; Petri precondition; Bugzilla `depends_on` graph (does *not* auto-set a status) | derive from the `advances` graph; **no field** |
| **External / resource wait** (vendor, hardware delivery, a specific person) | Azure "Impediment" item; GTD "Waiting For" list; GitLab scoped label | stored overlay + reason; exogenous, cannot be derived |
| **Time-based deferral** (postpone) | MS Project "Start No Earlier Than"; OmniFocus *defer date*; Things "When"; GTD *tickler* | overlay + `until` date that **auto-resurfaces** at read time |
| **Human decision** (choose/approve) | — | **already `human_gate: decision/session`** ✓ |
| **Rejected** (won't do) | Bugzilla WONTFIX (terminal) vs DEFERRED (still to-do) | **already `disproved`/`superseded`** ✓ |

`human_gate` is the proof-of-pattern: GoC already models one block-kind
(decision-wait) as a typed first-class mechanism rather than a generic status.

## Two secondary findings

- **The single edge is Finish-to-Start only.** Precedence theory (PDM) has four
  dependency types — FS (what `advances` is), Start-to-Start, Finish-to-Finish,
  Start-to-Finish — plus **lead/lag** as *edge* metadata. Deferred (see Decision
  point 6), but the model must not assume FS == dependency.
- **Aging/escalation lifecycle (Kanban).** A *waiting* item carries an expected
  date (SLE); when the date elapses it **escalates to blocked** (andon). This is
  why the overlay carries `waiting_until` and `goc validate` surfaces elapsed
  waits. *Class of service* (urgency) is a separate orthogonal axis from
  block-reason; out of scope here but noted.

## The three motivating questions, answered by the literature

1. **Walk `advances` upstream to find blockers?** Yes for card-blocks-card —
   the CPM/Petri/Asana/GitLab model, which GoC already walks. But the graph is
   structurally blind to non-card blockers (delivery, person, time).
2. **How does a blocked card discover it is unblocked?** Make dependency-block
   *derived* and it discovers itself. Stored `blocked` is the Jira problem
   (no native auto-transition; cards get stranded).
3. **Is `blocked` too generic?** Unanimously yes — each kind resolves by a
   different mechanism.

## Sources

**Lean / Kanban / TOC**
- djaa.com — [WIP limits for blocked vs waiting items](https://djaa.com/kanban-evergreen-should-we-include-waiting-or-blocked-items-in-wip-limits/)
- nkdagility — [Blocked columns obfuscate workflow](https://nkdagility.com/resources/blog/blocked-columns-on-kanban-boards-obfuscate-workflow-and-undermine-effectiveness/)
- LEANability — [Blocker clustering in practice](https://www.leanability.com/en/blog/2017/05/blocker-clustering-in-practice/)
- Kanban Tool — [Classes of Service](https://kanbantool.com/kanban-guide/classes-of-service)
- Nave — [Managing blocked work in Kanban](https://getnave.com/blog/blocked-work-in-kanban/)

**Formal state / workflow modelling**
- Harel — [Statecharts: A Visual Formalism for Complex Systems (1987)](https://www.sciencedirect.com/science/article/pii/0167642387900359)
- statecharts.dev — [State explosion](https://statecharts.dev/state-machine-state-explosion.html) · [Parallel (orthogonal) state](https://statecharts.dev/glossary/parallel-state.html) · [Guard](https://statecharts.dev/glossary/guard.html)
- Workflow Patterns — [Milestone (WCP18)](http://www.workflowpatterns.com/patterns/control/state/wcp18.php) · [Deferred Choice (WCP16)](http://www.workflowpatterns.com/patterns/control/state/wcp16.php)
- van der Aalst — [Petri Nets to Workflow Management](https://users.cs.northwestern.edu/~robby/courses/395-495-2017-winter/Van%20Der%20Aalst%201998%20The%20Application%20of%20Petri%20Nets%20to%20Workflow%20Management.pdf)

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
