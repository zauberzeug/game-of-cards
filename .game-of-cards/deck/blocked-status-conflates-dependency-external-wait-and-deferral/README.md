---
title: blocked-status-conflates-dependency-external-wait-and-deferral
summary: "`status: blocked` is one generic state covering four distinct situations with different resolution mechanisms: a card-dependency (derivable from the advances graph), an external/resource wait (no card, often a date), a deferral (time-based snooze), and a human decision (already typed as human_gate). Design pass needed to decide which become first-class and which derive."
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
  - [ ] Design decision recorded: which block-kinds become first-class mechanisms vs. derived vs. left as prose, and whether `blocked` stays a stored status, becomes a derived state, or becomes an overlay/flag.
  - [ ] Decision on card-dependency blocking: keep `STALE_BLOCKED` as warn-only, or upgrade to derived/auto-clear (and if derived, whether `blocked` is computed rather than hand-set).
  - [ ] Decision on the genuinely-missing case: typed wait/defer with optional until/expected date (covers external delivery, resource/person, postpone), including whether it auto-resurfaces on the date.
  - [ ] Relationship to `human_gate` clarified: human-decision-wait is already typed; the spec must say how `waiting`/`blocked` compose with (or stay distinct from) the gate.
  - [ ] If new schema fields result: schema.yaml + card-schema skill + emitter + `goc validate` coverage; if behavior-only: engine + skills updated. Either way the advance-card skill's blocked guidance is rewritten to match.
---

# `blocked` is one generic status where the industry uses several distinct mechanisms

GoC models "stuck" as a single `status: blocked`. Research into how other
systems (Jira, Linear, Asana, Azure DevOps, kanban practice) handle stuck work
shows "blocked" decomposes into **four situations with different resolution
mechanisms** — and GoC has already, accidentally, solved one of them cleanly.

## The kinds of "stuck"

| Kind | Resolves by | Date? | GoC today |
|---|---|---|---|
| **Card-dependency** — an upstream work item must finish first | that card closing | no | `advanced_by` edge + manual `status: blocked`; `STALE_BLOCKED` warns when all prereqs are terminal |
| **External wait** — vendor, client, hardware delivery | an outside event | often an **expected date** | body prose only |
| **Resource wait** — a specific person/skill unavailable | the person frees up | sometimes | body prose only |
| **Human decision** — needs a person to choose/approve | a human answers | no | **already first-class: `human_gate: decision/session`** |
| **Deferral / postpone** — deliberately parked for now | time passing | **until-date** | nothing (Linear: *snooze*, auto-returns on date or new activity) |

The key realisation: `human_gate` is "blocked on a human decision," modelled as
a typed mechanism rather than a generic status. That is the proof-of-pattern
for treating block-*kind* as first-class.

## What the engine actually does today

- `validate_blocker_coherence` (`engine.py:1118`) reads `advanced_by` as the
  blocker set (`engine.py:1153`) — i.e. GoC already *walks the graph upstream*
  to find what blocks a card. This is the Asana/Linear card-dependency model.
- But it only **warns** (`STALE_BLOCKED`); it does not **clear**. Un-blocking is
  a manual `status` flip. GoC sits in the Jira camp (manual, no auto-transition)
  while owning the data for the Asana/Linear camp (derived, auto-clear).
- `advanced_by` is the *value-flow* inverse edge, reused here for *precedence* —
  the conflation tracked by
  [closed-card-relationship-edges-stay-first-class-in-the-deck-graph](../closed-card-relationship-edges-stay-first-class-in-the-deck-graph/)
  and originally designed in
  [rename-blocks-to-advances-and-design-value-sort](../rename-blocks-to-advances-and-design-value-sort/).

## The three questions that motivated this card

1. **Can we just walk `advances` upstream to find blockers?** Yes — for
   card-blocks-card. But the graph is structurally blind to non-card blockers
   (delivery, person, time): there is no upstream card to walk to. Graph-walk
   covers ~one of the kinds.
2. **How does a blocked card discover it is unblocked?** Derived (Asana/Linear:
   blocker closes → auto-clear; Linear flips the flag orange→green) vs. manual
   (Jira: no native auto-transition). For the card-dependency case the clean
   answer is to *derive* blocked-ness rather than store it — then un-blocking
   discovers itself, and no `blocked_by` field is needed.
3. **Is `blocked` too generic?** Yes — confirmed. Each kind resolves by a
   different mechanism, so a single status cannot carry the resolution signal.

## Prior art

- **Jira** — three mechanisms with different semantics: a *Blocked status*
  (loses workflow position — widely argued against, "thou shalt not have a
  blocked status"), a *flag* (overlay; card stays put, remove flag to clear —
  the recommended approach), and an *"is blocked by" link* (relationship, no
  auto-status). **No native auto-transition** when the blocker resolves.
- **Asana / Linear** — blocking is a typed relation with **derived** unblocking:
  completing the blocker auto-recognises the dependent as unblocked. **Linear**
  additionally offers *snooze* — defer until a date or until new activity,
  whichever comes first (the deferral case).
- **Kanban practice** — distinguishes *blocked* (urgent, external impediment)
  from *on-hold / waiting* (expected wait, lower urgency, sometimes a "parking
  lot" with an expected end time). Blocker-reason categories (dependency,
  external, resource, awaiting info/approval) are standard; many tools attach an
  **expected date** to the wait.

## Proposed decomposition (for the design session)

A starting frame, not a settled plan:

- **Card-dependency** → *derive* from the `advances` graph; upgrade
  `STALE_BLOCKED` from warn → auto-clear. No new field. (Resolves Q1/Q2.)
- **Human decision** → already `human_gate`. Leave as-is; document the relation.
- **External / resource wait** → the genuinely missing expressiveness: a typed
  `waiting`/`on_hold` overlay with a reason and an **optional expected/until
  date**. Not a card-to-card edge.
- **Deferral / postpone** → snooze-until-date that auto-resurfaces the card on
  the date. May be the same mechanism as the wait overlay with a different
  reason, or its own thing.
- **Mechanism question** (cross-cutting): should "stuck" be a *status*, a
  *derived state*, or an *overlay/flag* on an otherwise-open card? Jira practice
  favours overlay; GoC currently uses status.

## Open questions for the session

- Is `blocked` retired in favour of `waiting`/`on_hold` + derived dependency
  state, or kept as an umbrella with a typed reason sub-field?
- Does an until-date imply a scheduler/resurface hook, or is it advisory only
  (surfaced by `goc validate` / standup)?
- How do the new mechanisms compose with `human_gate` and with the loop-safety
  filter `pull-card` uses (`human_gate: none`)?

## Sources

- Scrum.org — [Blockers vs. On-hold](https://www.scrum.org/forum/scrum-forum/5602/blockers-vs-hold)
- Businessmap — [How to Deal with Blocked and Delayed Work](https://businessmap.io/blog/kanban-blocked)
- Kit Friend — [Thou shalt not have a "blocked" status in Jira](https://medium.com/the-pinch/thou-shalt-not-have-a-blocked-status-in-jira-9bcafde684b8)
- Atlassian — [Why flagging a Jira issue is so cool](https://community.atlassian.com/forums/Jira-articles/Why-flagging-Jira-issues-is-so-cool/ba-p/1872469)
- Linear — [Issue relations](https://linear.app/docs/issue-relations) and [Triage / snooze](https://linear.app/docs/triage)
- Asana — [Use dependencies to kick work off at the right time](https://help.asana.com/hc/en-us/articles/23567568831899-Use-dependencies-to-kick-work-off-at-the-right-time)
- Plane — [Project blockers: definition, examples](https://plane.so/blog/project-blockers-definition-examples-and-how-to-overcome-them)
- SmartSuite — [Dependency Field](https://help.smartsuite.com/en/articles/8609918-dependency-field)
