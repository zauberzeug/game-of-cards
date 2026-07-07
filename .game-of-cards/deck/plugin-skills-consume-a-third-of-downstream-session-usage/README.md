---
title: plugin-skills-consume-a-third-of-downstream-session-usage
status: active
stage: null
contribution: high
created: "2026-07-07T04:03:31Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
summary: |-
  A downstream project's plugin-usage report attributes 31% of its session
  usage to the GoC plugin — almost entirely the workhorse skill bodies
  (finish-card 15%, create-card 8%, advance-card 3%, decide-card 3%,
  next-card 2%). Each body ships the complete edge-case manual on every
  invocation and persists in context for the rest of the session.
  Restructure the hot-path skills for progressive disclosure: a happy-path
  core in SKILL.md plus a sibling reference.md read only when the edge
  case actually arises. Supersedes the lean/full-variant design.
definition_of_done: |
  - [ ] TDD: a regression test caps the byte size of hot-path skill bodies (create-card, finish-card, advance-card, decide-card, next-card, pull-card, card-schema) — red on today's sizes (advance-card 17,932 B; card-schema 44,375 B) before the restructure, green after.
  - [ ] MECHANICAL: finish-card, create-card, advance-card, and decide-card SKILL.md restructured to a happy-path core + `reference.md` sibling; no guidance deleted — every moved section lands verbatim-or-tightened in the sibling with a one-line routing pointer left in the core.
  - [ ] MECHANICAL: card-schema SKILL.md split the same way — lookup-shaped core (fields, enums, canonical tags, title rules, DoD format) stays; rationale/contract essays move to `reference.md`.
  - [ ] MECHANICAL: finish-card's duplicate `!cat .game-of-cards/hooks/finish-card.md` injection (Step 2 + Step 7) collapsed to a single load.
  - [ ] EMPIRICAL: before/after byte counts for every restructured skill recorded in log.md; the per-card-cycle hot-path load (scan-deck + create-card + advance-card + finish-card) drops ≥ 50%.
  - [ ] PROCESS: `heaviest-skills-re-load-full-methodology-briefing-per-card-cycle` marked superseded --by this card; its log.md carries the supersession rationale.
  - [ ] PROCESS: only `goc/templates/skills/` and `tests/` hand-edited; `python scripts/sync_plugin_assets.py --check` and `python3 scripts/port_skills_to_openclaw.py --check` pass; `uv run goc validate` and the full unittest suite pass.
supersedes:
  - heaviest-skills-re-load-full-methodology-briefing-per-card-cycle
worker: {who: Rodja Trappe, where: main}
---

# Plugin skills consume a third of downstream session usage

## Location

`goc/templates/skills/{finish-card,create-card,advance-card,decide-card,card-schema}/SKILL.md`
(source of truth; auto-synced into `claude-plugin/`, `codex-plugin/`,
`.claude/skills/`, `.codex/skills/`, and hand-ported into
`openclaw-plugin/`).

## What's broken

A downstream consumer's plugin-usage report attributes **31% of total
session usage** to the GoC plugin:

| Skill | share | body size |
|---|---:|---:|
| finish-card | 15% | 16,669 B |
| create-card | 8% | 17,430 B |
| advance-card | 3% | 17,932 B |
| decide-card | 3% | 11,477 B |
| next-card | 2% | 6,549 B |

The shares track body size × invocation frequency. Two multipliers make
raw size worse than it looks:

1. **Skill bodies persist.** Once a skill loads, its body stays in the
   conversation and is re-sent (as cached input) on every subsequent
   turn. One card lifecycle (scan-deck → create-card → advance-card →
   finish-card) parks ~60 KB (~15k tokens) of methodology text in
   context before any actual work happens.
2. **Every invocation ships the complete manual.** Bundled closures,
   `advanced-by-closed` retraction, post-close amendments, the
   edge-vs-tag modeling essay, the three coordinating-card shapes —
   edge-case material that applies to a minority of invocations rides
   along on all of them. finish-card additionally `!cat`s the same
   project hook file twice (Step 2 and Step 7), injecting its content
   into context twice per invocation.

`card-schema` (44,375 B, ~11k tokens) is not in the report's top five
but is cross-referenced ~40 times from the other skill bodies; any
session where it fires pays the full manual for what is usually a
single field-semantics lookup.

## Why it matters

This is a permanent tax on every consuming repo, paid in the consumer's
usage budget, and it buys no capability the session actually uses —
the edge-case prose is read past, not acted on, in the typical
invocation. 31% of a downstream project's limit went to plugin overhead
before any of that project's own work. Unlike the autonomous-loop
framing of the superseded card, the report shows the cost lands on
*deliberate, human-paced* usage too — which removes the main argument
for keeping the full manual as the default surface.

## Fix — progressive disclosure, not skill variants

The superseded card
([`heaviest-skills-re-load-full-methodology-briefing-per-card-cycle`](../heaviest-skills-re-load-full-methodology-briefing-per-card-cycle/))
proposed `<verb>-lean` sibling *skills* and left routing (who invokes
which variant?) as an open session-gated decision. The usage report
dissolves that question: deliberate use pays the same cost, so there is
no audience for a fat default. A single skill restructured for
**progressive disclosure** needs no routing at all:

- **SKILL.md keeps the happy path**: the invocation triggers, the
  step-by-step procedure, the CLI commands, the `!` dynamic-context
  hooks, and one-line safety rules (e.g. "never `git add -A` on shared
  main" stays; only its rationale moves).
- **A sibling `reference.md` carries the edge cases**: bundled
  closures, retraction guidance, post-close amendment format,
  edge-vs-tag essays, coordinating-card shapes, methodology rationale.
  The core ends with a short routing table: *situation → section to
  read*. The host never auto-loads siblings; the model Reads them from
  the skill's base directory only when the situation actually arises.
- The sibling-file mechanism is already proven end-to-end:
  `card-schema/schema.yaml` ships through `goc install`
  (`_iter_skill_assets`), both plugin syncs, and the OpenClaw porter's
  verbatim asset copy.

Scope: the four workhorse verbs (finish-card, create-card,
advance-card, decide-card) plus card-schema. next-card and pull-card
are already lean-ish and only gain the size-cap test; description
trimming is the sibling card
([`skill-descriptions-bloat-every-consumer-session-prompt`](../skill-descriptions-bloat-every-consumer-session-prompt/));
kickoff-skill consolidation is out of scope (separate filing).

## Empirical evidence

Downstream usage report (2026-07-06, verbatim shares): plugin total
31% = finish-card 15 + create-card 8 + advance-card 3 + decide-card 3
+ next-card 2. Template byte sizes measured on this repo at HEAD
(`wc -c goc/templates/skills/*/SKILL.md`): totals 224,554 B across 18
skills; the five in-scope bodies sum to 107,883 B.
