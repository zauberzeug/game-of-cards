---
name: pull-card
description: "Pull the highest-leverage `human_gate: none` open card off the queue, claim it, work it, close it, commit. AUTO-INVOKE when the user says \"drain the queue\", \"pull a card\", \"let the agents work\", \"autonomous mode\", \"make progress\", or when invoked via /loop or /schedule." If the catalog location path is unreadable, fetch the body via the goc tool verb "skill", args ["pull-card"].
---

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

`goc --status active -v 2>&1 | head -20`

Treat any listed active card as a soft lock. Do not claim the same card,
or adjacent/conflicting work, unless the user explicitly asks to continue
that active card.

Pick the highest-contribution **ready** card (`--ready` filters to
`status: open` ∧ `human_gate: none` ∧ no active `waiting_on` overlay
— dependency-readiness is advisory display only, an `advances` prereq
that is still open shows up as "awaiting" but does NOT hide the card
from the queue):

`goc --ready -v 2>&1 | head -22`

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

1. the `advance-card` skill (with `<title> active`) to claim. (The status flip is
   the soft lock against parallel sessions.)
2. Read the body, the DoD, and any referenced files.
3. Implement.
4. the `finish-card` skill (with `<title>`) to close (DoD-gated), then commit the work and closure.

The card body is the briefing the original filer wrote. Trust it.

## Fixing what you surface (fix-through)

A pull-card session routinely *surfaces* new defects while working its
card — a sibling bug in the same function, an adjacent one-liner, a
missing guard — or finds one when the queue is empty. The reflex
inherited from the `audit-deck` skill is "flag, don't fix": file a card
and leave it. **But that reflex is audit's, not the worker's.** A
session that already has the relevant code loaded and the diagnosis
done is the *cheapest* place to land a small fix; deferring it to a
separate fresh-context run that must rediscover, reload, and re-diagnose
is pure overhead.

So **fix it through** — file the card, then claim → implement → close
it in the same session — when **all** of these hold:

- **Gate-free.** It would file at `human_gate: none`: the fix is
  determined, with no decision or taste call between credible
  alternatives.
- **Small and single-site.** The fix is mechanically clear and bounded
  — rule of thumb, ~one source file plus its regression test. If it
  fans out across modules, it is not fix-through.
- **Not a meta-fix.** It is not the Nth instance of a root-cause shape
  that should become one architectural card (the audit-deck
  sibling-sweep rule). Four instances of one shape is a deliberate
  decision — file it, don't inline it.
- **Close to loaded context.** It lives in code this session already
  has in focus. A defect spotted in a far-off module is fixed better by
  a fresh run with *that* module loaded — file it and move on.

**Always file the card** (the `create-card` skill), even when you fix it
seconds later. The card is the record axis, and its DoD carries the TDD
contract — the regression test that proves the fix. Fix-through removes
the wasted second *run*, not the card. Each fix-through finding is its
own card and its own commit, kept separate from the card you pulled.

When a finding does **not** clear the bar — it needs a decision, fans
out across the codebase, is a meta-fix family, or sits far from your
loaded context — file it and leave it in the queue. The fresh-context
separation earns its cost there.

**Fix-through is not "drain the queue."** Close the card you pulled
plus at most the small defect(s) it entangled, then exit. One pull per
run, with fresh context as the default, stays the operating rhythm
(`/loop` and the cloud `pull-card` workflow re-trigger for the next
card) — fix-through just stops you from leaving a small, ready fix on
the floor for a second run to trip over.

## When to stop without finishing

- **Queue empty.** No ready cards. Invoke the `audit-deck` skill to file
  one new card from emergent codebase observations. If that finding is
  **fix-through-eligible** (see "Fixing what you surface" above), work
  it to close in this same session instead of exiting. Otherwise — a
  decision-class, cross-cutting, or meta-fix finding — file it and exit;
  the next invocation can work it.

- **Decision-class question — try the project-specific consultation
  BEFORE raising the gate.** The body reveals the card needs a
  judgement call (mechanism choice, convention, default value, scope
  reframing, lit-anchored default). The Andon cord is lazy: agents
  try the project-local consultation first, then pull.

  `cat .game-of-cards/hooks/pull-card.md 2>/dev/null || true`

  1. If the consuming repo defined a consultation skill or rubric in
     the hook above, follow it. **If it answers confidently:** record
     the resulting decision via the `decide-card` skill (with `<title>
     --decision "<choice>" --because "<consultation-name>:
     <one-line>"`) (the `--because` should cite whatever rubric the
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

or, when you fixed through a finding you surfaced:

```
closed <pulled-title>; fixed-through <surfaced-title>: <one-line>
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
