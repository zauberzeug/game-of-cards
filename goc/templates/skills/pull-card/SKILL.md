---
description: Pull the highest-leverage `human_gate: none` open card off the queue, claim it, work it, close it, commit. AUTO-INVOKE when the user says "drain the queue", "pull a card", "let the agents work", "autonomous mode", "make progress", or when invoked via /loop or /schedule.
---

# Pull a card

Kanban's foundational principle (Anderson) is **pull-based work
intake**: a worker takes the next item when capacity exists, rather
than having work pushed at them. This skill is the autonomous worker —
it pulls one card off the queue, works it end-to-end, commits.

The pull principle is what makes autonomous operation *safe*. Work
isn't shoved at agents on a timer; agents pull on their own terms,
filtered to `human_gate: none`. The human steers by curating WHAT'S
in the queue and at what gate.

## What to do

Pick the highest-contribution `human_gate: none` open card:

!`goc --status open --human-gate none -v 2>&1 | head -20`

Then:

1. `Skill(advance-card) <title> active` to claim. (The status flip is
   the soft lock against parallel sessions.)
2. Read the body, the DoD, and any referenced files.
3. Implement.
4. `Skill(finish-card) <title>` to close + commit.

The card body is the briefing the original filer wrote. Trust it.

## When to stop without finishing

- **Queue empty.** No `human_gate: none` open cards. Invoke
  `Skill(extend-deck)` to file one new card from emergent codebase
  observations, then exit. The next invocation can work it.

- **Research-impacting question — try /mindset BEFORE raising the
  gate.** The body reveals the card is research-impacting (framework
  derivation, mechanism choice, sign convention, new primitive,
  lit-anchored default, publication-tier reframing). The Andon cord
  is lazy: agents try `/mindset` first, then pull.

  1. Invoke `Skill(mindset)`. The skill loads the full vision /
     axioms / plasticity context.
  2. Apply principles to the parked question. Ask: is the answer
     determined by axiom citation (A1/A4 universal vs.
     A3/A5/A6/A7 architectural) plus primary-source backing
     (paper / textbook / framework doc section)?
  3. **If /mindset answers confidently:** record the decision via
     `Skill(decide-card) <title> --decision "<choice>" --because
     "/mindset: <principle> — <one-line application>"`. The
     `--because` MUST cite the mindset principle invoked (e.g.,
     `/mindset: A6 striosome/matrix separation — motors aren't
     predicting environment features, so Branch 1 conflates action
     with prediction`). Then continue working the card from the
     decision: implement, close, commit.
  4. **If /mindset is ambiguous, OR the question is non-bio-faithful
     in nature** (resource allocation, scope split, deadline,
     multi-stakeholder alignment, taste call, missing primary-source
     evidence): raise the gate to `decision` or `session`, write
     a `## Decision required` body section, commit the gate-and-body
     update. The human will see the parked card.

  This keeps the human out of the loop when bio-faithful reasoning is
  decisive. The cord still gets pulled — just not for questions
  /mindset already answers.

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
because impact:high". The commit message and closure log already say
what happened. The report is the index, not the story.

## Pairs naturally with

- `/loop pull-card 30m` — drains the queue while the user works in
  another session.
- `/schedule pull-card weekday 09:00` — opens the day with one card
  closed.
- `/schedule extend-deck weekly` — keeps the queue fed; the
  pull-principle requires something to pull.
- `/schedule improve-deck monthly` — hygiene pass.
