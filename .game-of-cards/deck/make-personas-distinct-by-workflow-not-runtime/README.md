---
title: make-personas-distinct-by-workflow-not-runtime
summary: "Refactor PERSONAS.md to lead with a single-audience framing — 'AI-first users with a project folder' — and treat vibe-coder, solo developer, and multi-agent operator as three on-ramps into ONE audience rather than separate personas. Today's PERSONAS.md mixes four axes under one numbered list: workflow shape (#1-3), runtime channel (#4 OpenClaw consumer), engineering constraint (#5 classical-dev team), and domain (#6 agent runtime as to-do engine). The mix creates false distinctness: a vibe-coder using OpenClaw is still a vibe-coder; a recipe-writer is structurally the same AI-first user as a vibe-coder on a code repo. New shape: one audience paragraph, three on-ramps with the vibe-coder section explicitly extending to non-code AI-first projects, a variations/configuration section absorbing OpenClaw/runtime/single-vs-multi-agent/deck-visibility, anti-fits collapsed to two real ones (heavy tracker users, multi-maintainer OSS with strict commit hygiene). Keep PERSONAS.md filename. README.md line 13's 'five personas' link copy gets corrected. The website already does the right thing (three persona cards + OpenClaw under install) — no website changes."
status: done
stage: null
contribution: medium
created: "2026-05-14T13:33:24Z"
closed_at: "2026-05-14T13:53:06Z"
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [x] PERSONAS.md rewritten: leads with the audience named as "AI-first projects" and frames the three on-ramps (vibe-coder, solo developer, multi-agent coordinator) as illustrations of one fit, not separate use cases.
  - [x] Vibe-coder on-ramp explicitly extends to non-code AI-first projects (recipes, writing, research) with a callout pointing at `support-custom-card-workflows-and-statuses` as the one real engine gap.
  - [x] Variations/configuration section absorbs runtime channel (Claude Code / OpenClaw / generic CLI), deck visibility (checked-in / gitignored), and single-vs-many agents — explicitly framed as orthogonal to the audience.
  - [x] Anti-fits trimmed to two real audiences GoC doesn't serve yet: heavy Jira/Linear adopters (integration pending), multi-maintainer OSS with strict commit hygiene (external-deck epic pending; solo OSS gitignore recipe still pointed to from DECK_LOCATION.md).
  - [x] README.md lede (line 7) leads with the "AI-first projects" framing before enumerating the three on-ramps; cross-ref to PERSONAS.md updated — "five personas" link copy corrected to match the new shape.
  - [x] site/index.html `who-intro` paragraph updated to lead with "Game of Cards is for AI-first projects" and drop the stale "Three audiences ... two more" wording. Three persona cards and anti-persona block unchanged.
  - [x] DECK_LOCATION.md cross-refs to PERSONAS.md still resolve to live sections after the rewrite; "Persona served" → "Audience served" rewording lands on every relevant block.
  - [x] No content lost: every existing trade-off, anti-persona consideration, and "how to choose" cue is either preserved in the new shape or intentionally dropped with a documented reason.
worker: {who: Rodja Trappe, where: main}
---

# Refactor PERSONAS.md around one audience with three on-ramps

## Why now

The OpenClaw plugin shipping made the category error in PERSONAS.md visible: persona #4 "The OpenClaw consumer" is a *runtime channel*, not a workflow shape. Its body openly admits this — "May also be a vibe-coder, a solo developer, or a multi-agent coordinator; what is distinctive is the runtime they walk in with" — and "How to choose" tells the reader that runtime-persona and workflow-persona *stack rather than compete*. That's not a persona; it's a configuration variable.

Pulling that thread, the rest of the list unravels too:

- **#1 vibe-coder, #2 solo developer, #3 multi-agent coordinator** — same use case (in-folder work management for a project with one or more AI agents). They differ in *how the human relates to the work*, not in *how GoC is used*.
- **#4 OpenClaw consumer** — distribution channel, orthogonal.
- **#5 classical-development team (transitional)** — a constraint cross-cutting the others (strict commit hygiene), not a workflow.
- **#6 agent runtime as to-do engine (future)** — the only entry that lists a genuinely different need (non-code domain, custom statuses, git-decoupled engine). But two of its three claimed barriers are already false today: `kickoff-and-install-handle-non-git-directories` closed the git-required assumption, and closure-equals-commit is doc convention not engine enforcement. The one real gap is custom statuses, tracked by `support-custom-card-workflows-and-statuses`.

The website already does the right thing: three persona cards in the hero section, OpenClaw mentioned under install. PERSONAS.md is the file out of step.

## Framing

**One audience today**: AI-first users with a project folder. Humans working with one or more AI agents who want in-folder task memory the agent can read and write. The deck is files; optionally git-backed for cross-session and cross-agent visibility.

**Three on-ramps into that audience** (not separate use cases — different value props of the same fit):

1. **The vibe-coder** (AI-first): doesn't read code, agent owns the cards. Same shape extends to non-code AI-first projects — recipe books, research workflows, long-form writing — wherever the human stays at the prompt and the agent does the doing. Today's tooling assumes a code project in its examples; the engine is domain-agnostic; the one real gap for non-code is custom statuses.
2. **The solo developer** (AI-augmented): code-fluent, replaces TODO.md, uses DoD to keep the agent honest across sessions.
3. **The multi-agent operator**: many AIs converging on one repo; claim protocol + gates prevent collision; this is the maintainer's own primary use case.

**Variations within the audience** (configuration, not persona): runtime channel (Claude Code / OpenClaw / generic CLI), deck visibility (checked-in / gitignored), single vs many agents.

**Audiences GoC doesn't serve yet** (real anti-fits):

- Heavy Jira / Linear / tracker adopters — integration pending (`integrate-github-issues-discussions-and-pull-requests`, `explore-saas-deck-hosting-with-optional-tracker-sync`).
- Multi-maintainer OSS with strict commit hygiene — external-deck epic pending (`support-external-game-of-cards-state-location`). Solo OSS maintainers have the gitignored-deck recipe today; multi-maintainer needs the epic to ship.

(Old "feature planner without autonomous loop" anti-persona is dropped — it's too narrow to be an audience, and the loop is core enough to GoC that opting out makes the tool the wrong choice trivially.)

## Surfaces to update

- `PERSONAS.md` — full content rewrite under the framing above. Filename unchanged.
- `README.md` — line 13 currently says "five personas, anti-personas, and which workflow shape each one accepts"; rewrite to match the new shape (three on-ramps, two anti-fits, no count needed).
- `DECK_LOCATION.md` — verify any references to PERSONAS.md still resolve (search for anchor links; the OSS-maintainer recipe section explicitly links here).

## Anti-scope

- No structural website changes. `site/index.html` already shows three persona cards + OpenClaw in install, and that structure stays — only the `who-intro` paragraph is rewritten because the previous "Three audiences ... two more" wording was written against the old six-persona PERSONAS.md and now misrepresents the new shape.
- No skill or engine changes — this is documentation only.
- No rename of `PERSONAS.md`. Keeping the filename avoids cross-repo / external-link churn and the word "persona" is still accurate for the three on-ramps as a UX device.
