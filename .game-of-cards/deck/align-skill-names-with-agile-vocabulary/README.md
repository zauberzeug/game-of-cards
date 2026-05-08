---
title: align-skill-names-with-agile-vocabulary
summary: "The current 12-skill surface is consistent (`<verb>-card` / `<verb>-deck`) but speaks Jira/CRUD, not the XP+Kanban+Scrum vocabulary that GoC's philosophy actually borrows from. Realign two skill names and add two new skills so the surface advertises the methodology lineage out loud and fills two genuine gaps. Renames: `extend-deck` → `audit-deck` (the skill inspects existing artefacts for defects/inconsistencies — that is an audit / code review, not an XP spike, which would be a learning experiment; the misnomer was a quiet conceptual leak). `improve-deck` → `refine-deck` (Scrum Backlog Refinement is the precise term for what the skill does — retag stale, prune unverified parks, surface defunct file:line references). New skills: `standup` (a quick daily-style read of the deck — what is `active`, what is `blocked` and why, what was closed since yesterday in `log.md`, what is waiting on a decision-gate; today reachable only by combining `scan-deck` + `git log` + manual reading) and `retrospective` (backwards analysis of the last N closed cards: cluster by tag, surface recurring failure modes, propose generalization-card candidates, give a rough velocity feel; today nothing covers this — `extend-deck` hunts NEW defects but never looks at completed work). Renames are full breaks with no aliases — the project is still young and the surface should be clean before plugin downloads grow."
status: done
stage: null
contribution: medium
created: 2026-05-08
closed_at: 2026-05-08
human_gate: none
advances: []
advanced_by: []
tags: [story]
definition_of_done: |
  - [x] Templates renamed: `goc/templates/skills/extend-deck/` → `audit-deck/`; `goc/templates/skills/improve-deck/` → `refine-deck/`. Plugin duplicates at `claude-plugin/skills/` renamed in lockstep and the CI byte-for-byte template-vs-plugin check still passes
  - [x] Skill bodies updated to reflect new names: AUTO-INVOKE descriptions, internal cross-references, and any wording that named the skill itself (e.g. "improve-deck does X" → "refine-deck does X")
  - [x] New skill `standup` created at `goc/templates/skills/standup/` (and plugin duplicate). Body specifies: list `active` + `blocked` cards with blocker reason; show closures from `log.md` files within last 24h (configurable N); surface `human_gate: decision|session` cards waiting on a human; read-only, never mutates state
  - [x] New skill `retrospective` created at `goc/templates/skills/retrospective/` (and plugin duplicate). Body specifies: read last N (default 10) closure entries across all `log.md` files; cluster by tag; surface cards whose closure mentions a recurring problem (generalization candidate); read-only suggestion mode — may *propose* `Skill(create-card)` invocations for generalization candidates but does not file them
  - [x] AUTO-INVOKE descriptions for the two new skills include realistic trigger phrases (standup: "what's up", "where do we stand", "what's blocked", "daily check"; retrospective: "what have we learned", "review recent work", "any patterns lately", "look back")
  - [x] All references updated in lockstep: `AGENTS.md` skill table, `CLAUDE.md` GoC marker block (via `goc/templates/AGENTS_GOC.md` and `goc/templates/CLAUDE_GOC.md`), README skill-surface listing, hook scripts (`deck_session_start.py`, `deck_prompt_router.py` — both template and plugin copies), `card-schema` skill cross-references
  - [x] No backward-compat aliases: old `extend-deck` and `improve-deck` folders removed from templates, plugin, and any installed test fixture; old names removed from documentation
  - [x] Smoke check: fresh `goc install` in a scratch repo lists exactly the new skill set (`audit-deck`, `refine-deck`, `standup`, `retrospective` present; `extend-deck`, `improve-deck` absent)
worker: {who: "claude[bot]", where: main}
---

# align-skill-names-with-agile-vocabulary

## The vocabulary leak

GoC openly inherits from XP (story cards, system metaphor, refactor
mercilessly), Kanban (pull system, explicit policies, WIP visibility),
and Scrum (Definition of Done, backlog refinement). The skill surface
today only advertises that lineage in two places: `pull-card` (Kanban
pull) and the DoD machinery. Everything else reads like Jira CRUD.

The two renames remove genuine misnomers, not just rebrand:

| Old           | New           | Why the new name is the right one                                                                                          |
|---------------|---------------|----------------------------------------------------------------------------------------------------------------------------|
| `extend-deck` | `audit-deck`  | "Extend" undersells the skill (it doesn't just append). It inspects existing artefacts for defects — that's an audit.       |
| `improve-deck`| `refine-deck` | Scrum Backlog Refinement is the exact term for retag-stale / prune-parks / surface-defunct-references. Drop-in fit.        |

`extend-deck` was loosely associated with "XP spike" in earlier
discussions — that was wrong. A spike is a time-boxed *experiment to
learn* (e.g. "can library X handle our load?"). `audit-deck` does not
experiment; it inspects.

## The two new skills fill real gaps

**`standup`** answers the daily question: *what's running, what's
stuck, what's new since yesterday, what waits on me?* Today this view
is reachable only by combining `scan-deck` (browse), `git log` (recent
closures), and manual reading of `log.md` files. The skill collapses
that into one read.

**`retrospective`** looks *backwards* at completed work — something no
existing skill does. `audit-deck` (formerly `extend-deck`) hunts NEW
defects in the codebase. `retrospective` reads the last N `log.md`
closure entries, clusters by tag, and surfaces patterns: which failure
modes recur, which closures mention the same root cause, which clusters
are candidates for a generalization card. It is read-only; it can
*propose* a `Skill(create-card)` invocation for a generalization
candidate but never files one itself.

## Why no aliases

The instinct to alias old names → new names is wrong here. Aliases
double the surface area, leak old vocabulary into AUTO-INVOKE
descriptions, and make the rename feel reversible. The project is
young; muscle memory is shallow; downloads are small. Clean break.

## Sequencing

This card and `rename-bootstrap-to-kickoff-as-onboarding-dialog` are
siblings under the same vocabulary-alignment effort. They are not hard
dependencies on each other and may ship in either order; doing them in
the same release minimises churn for consumers.

## Out of scope

- Renaming `bootstrap` → `kickoff` (separate card,
  `rename-bootstrap-to-kickoff-as-onboarding-dialog`).
- Adding more agile-flavoured skills beyond `standup` and
  `retrospective`. Other candidates (e.g. `swarm`, `wip-check`) can be
  proposed as separate cards once these two are in use.
- Renaming card-CRUD verbs (`create-card`, `advance-card`,
  `finish-card`, `decide-card`). They are clear, consistent, and the
  card metaphor is core to the product name; "story" rebranding
  rejected.
