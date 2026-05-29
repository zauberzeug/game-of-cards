---
title: kickoff-offers-autonomy-setup-options
summary: |-
  `Skill(kickoff)` ends after Stage 5 with "deck is live" and a hand-off
  to host complements. It never surfaces the autonomy options
  (`/loop` + `pull-card`, cron, GitHub Action, manual session) that are
  GoC's primary differentiator. New users learn about autonomous
  card-pulling only by accident. Add a Stage 6 that explains the modes
  and asks which to set up.
status: done
stage: null
contribution: medium
created: 2026-05-10
closed_at: "2026-05-11T03:45:30Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation, story]
definition_of_done: |
  - [x] decision recorded below for which autonomy modes Stage 6 covers
  - [x] decision recorded for whether Stage 6 is host-agnostic or
        delegated to host complements
  - [x] `goc/templates/skills/kickoff/SKILL.md` updated with new stage
  - [x] consumer copy at `.claude/skills/kickoff/SKILL.md` re-synced
        (`goc upgrade --keep-local-skills` from a consumer repo, or
        in this dogfood repo edit both copies in lockstep)
  - [x] OpenClaw plugin's ported kickoff skill stays consistent
        (re-port via `scripts/port_skills_to_openclaw.py` if its
        skill body diverges)
  - [x] new stage is idempotent — re-running kickoff on a repo that
        already chose an autonomy mode skips the question
  - [x] `goc validate` passes (skill-parity tripwire stays green)
worker: {who: "claude[bot]", where: main}
---

# kickoff-offers-autonomy-setup-options

## What's missing

`goc/templates/skills/kickoff/SKILL.md` walks through:

1. State detection
2. GoC introduction
3. Persona question
4. Briefing-target choice
5. `goc install` confirmation
6. Hand-off

It never mentions:

- `/loop /pull-card` (Claude Code) or equivalent in OpenClaw — drain
  the queue from a separate session for max control.
- A cron job that runs `pull-card` on an interval — fully unattended
  drain on the user's own machine.
- A GitHub Action that runs `pull-card` on a schedule — unattended drain
  in CI, ideal for distributed teams.
- "Manual only" — the user just files cards and works them by hand.

These are GoC's whole differentiating value over plain markdown task
lists. Hiding them until the user stumbles on `Skill(pull-card)`
under-sells the methodology.

## Why it matters

A new user who finishes kickoff today sees a `goc` queue that they have
to manually claim and work. They have no signal that the deck was
designed for autonomous pulling. The first time someone runs `/loop
/pull-card` it is usually because someone else suggested it — not
because kickoff offered it.

Adding the stage is also an honest information-architecture move: the
choice (autonomous? supervised? CI-driven?) shapes how the user
configures Claude Code permissions, what they put in CLAUDE.md, and
whether they configure GitHub Actions. Better to ask once at kickoff
than discover the gap weeks later.

## Decision

*Resolved 2026-05-10:* Q1: Stage 6 covers four modes (loop, cron, GitHub Action, manual) with an explicit 'skip for now' option. Q2: Implement Stage 6 in the generic kickoff skill; host complements provide host-specific recipes.

*Reasoning:* Q1: each mode is one bullet to describe and skip-for-now keeps friction low. Q2: autonomy is a methodology concept, not a host concept.
## Sketch of Stage 6 body (if Option B + I)

```markdown
## Stage 6 — pick an autonomy mode

Skip this stage if `.game-of-cards/config.yaml` already records an
autonomy choice (re-running kickoff should not re-ask).

Otherwise:

> How would you like cards to be pulled off the queue?
>
> 1. **Manual** — you file cards and work them by hand. No setup.
> 2. **Supervised loop** — `/loop` (Claude Code) or equivalent in your
>    host runs `pull-card` on an interval inside a session you watch.
>    Best for trying GoC before automating further.
> 3. **Local cron** — a cron job runs `pull-card` unattended on your
>    machine. Best for solo workflows where you trust the agent to
>    drain `human_gate: none` cards overnight.
> 4. **CI / GitHub Action** — a workflow runs `pull-card` on a schedule
>    in CI. Best for shared decks across a team.

Record the choice in `.game-of-cards/config.yaml` under `autonomy:` so
re-running kickoff is a no-op. Hand off to the host complement for the
host-specific recipe.
```

## Notes

- Idempotency: store the answer in `.game-of-cards/config.yaml` so
  Stage 0's state-detection sweep can skip Stage 6 on re-run.
- The "Manual" option is important — some users will want to defer the
  decision. Offer it as a real choice, not a dismissal.
- This card pairs naturally with the existing
  `drain-pull-card-queue-per-cron-tick` (done) and
  `author-openclaw-kickoff-skill-for-host-specific-onboarding` (done)
  — they laid the foundations this stage now surfaces.
