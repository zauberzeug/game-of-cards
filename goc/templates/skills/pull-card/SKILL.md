---
name: pull-card
description: Pull the highest-leverage `human_gate: none` open card off the queue, claim it, work it, close it, commit. AUTO-INVOKE when the user says "drain the queue", "pull a card", "let the agents work", "autonomous mode", "make progress", or when invoked via /loop or /schedule.
---

## Preflight

If any `!` block below shows `goc: command not found`, `Permission for this action has been denied`, or `no such file or directory: .game-of-cards/deck/`, **stop and invoke `Skill(kickoff)` first**. Kickoff detects which setup step is missing (CLI not installed, Bash allowance not granted, project state not scaffolded) and walks the user through it. Re-invoke this skill only after kickoff completes.

# Pull a card

Kanban's foundational principle (Anderson) is **pull-based work
intake**: a worker takes the next item when capacity exists, rather
than having work pushed at them. This skill is the autonomous worker —
it pulls one card off the queue, works it end-to-end, commits.

The pull principle is what makes autonomous operation *safe*. Work
isn't shoved at agents on a timer; agents pull on their own terms,
filtered through the ready-to-pull predicate (`status: open`,
`human_gate: none`, no active `waiting_on` impediment). The human
steers by curating WHAT'S in the queue and at what gate; an explicit
impediment overlay (`waiting_on` / `waiting_until`) hides hard waits
automatically — `advances` edges are advisory and do NOT hide a card
from the queue.

## What to do

Check for already-claimed work first:

!`goc --status active -v 2>&1 | head -20`

Treat any listed active card as a soft lock. Do not claim the same card,
or adjacent/conflicting work, unless the user explicitly asks to continue
that active card.

Pick the highest-contribution **ready** card (`--ready` filters to
`status: open` ∧ `human_gate: none` ∧ no active `waiting_on` overlay
— dependency-readiness is advisory display only, an `advances` prereq
that is still open shows up as "awaiting" but does NOT hide the card
from the queue):

!`goc --ready -v 2>&1 | head -22`

The last line of `goc --ready` is a **leverage comparison**:
`Pulling <title> (value N). Highest gated card: <title> (value M, gate <kind>).`
When `M >> N` (≥3× higher value), the autonomous puller is about to
work a small card while a much higher-value card sits parked behind a
human gate — that's a signal to ping the human to lower the gate
(`decide-card` for `decision`, the human's session for `session`)
*before* draining low-value queue items. When the leverage is close,
just pull. The line is omitted when no gated cards exist or the queue
is empty.

Then:

1. `Skill(advance-card) <title> active` to claim. (The status flip is
   the soft lock against parallel sessions.)
2. Read the body, the DoD, and any referenced files.
3. Implement.
4. `Skill(finish-card) <title>` to close (DoD-gated), then commit the work and closure.

The card body is the briefing the original filer wrote. Trust it.

## When to stop without finishing

- **Queue empty.** No ready cards. Invoke
  `Skill(audit-deck)` to file one new card from emergent codebase
  observations, then exit. The next invocation can work it.

- **Decision-class question — try the project-specific consultation
  BEFORE raising the gate.** The body reveals the card needs a
  judgement call (mechanism choice, convention, default value, scope
  reframing, lit-anchored default). The Andon cord is lazy: agents
  try the project-local consultation first, then pull.

  !`cat .game-of-cards/hooks/pull-card.md 2>/dev/null || true`

  1. If the consuming repo defined a consultation skill or rubric in
     the hook above, follow it. **If it answers confidently:** record
     the resulting decision via `Skill(decide-card) <title>
     --decision "<choice>" --because "<consultation-name>:
     <one-line>"` (the `--because` should cite whatever rubric the
     hook prescribes). Then continue working the card from the
     decision: implement, close, commit.
  2. If no hook is defined, OR the consultation is ambiguous, OR the
     question is non-substantive in nature (resource allocation,
     scope split, deadline, multi-stakeholder alignment, taste call,
     missing primary evidence): raise the gate to `decision` or
     `session`, write a `## Decision required` body section, commit
     the gate-and-body update. The human will see the parked card.

  This keeps the human out of the loop when project-specific
  reasoning is decisive. The cord still gets pulled — just not for
  questions the project's own rubric already answers.

- **Fix fails verification.** Revert the work, append
  `## Disproved fix attempt YYYY-MM-DD` to log.md, leave the card
  open with new evidence.
- **Pre-commit refuses + research-impacting issue.** Pause for the
  human.

## What to report

Whatever happened, in one line of plain fact:

```
closed <title>: <one-line what-changed>
```

or

```
parked <title>: gate raised to <decision|session> — <reason>
```

or

```
queue empty; filed <new-title>
```

Don't narrate context — no "round N", no "via /loop", no "picked
because contribution:high". The commit message and closure log already say
what happened. The report is the index, not the story.

## Pairs naturally with

- `/loop pull-card 30m` — drains the queue while the user works in
  another session.
- `/schedule pull-card weekday 09:00` — opens the day with one card
  closed.
- `/schedule audit-deck weekly` — keeps the queue fed; the
  pull-principle requires something to pull.
- `/schedule refine-deck monthly` — hygiene pass.
