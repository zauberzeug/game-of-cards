---
description: Record a decision (what + why) on a parked card and lower the human gate from `decision` or `session` to `none`. AUTO-INVOKE when the user says "I decided X", "let's go with Y", "the answer is Z", "go ahead with", "approved", or otherwise resolves a parked card. The Andon-cord lowering action — pull-card raises the gate; this skill is the human's one-action handoff so pull-card can resume.
argument-hint: <title> --decision "<one-line what>" --because "<one-line why>"
---

# Decide a card

Lean's **Andon cord** (Toyota production system): when a worker hits a
problem they cannot resolve, they pull the cord; the line stops; a
supervisor walks over, resolves the *cause*, and restarts the line.
The system only works because both pulling AND lowering the cord are
cheap. If lowering took fifteen minutes, workers would route around
the cord and the whole quality system rots.

Our cord is `human_gate`. `Skill(pull-card)` raises it
(`none → decision` or `none → session`) when it hits a question only
a human can answer — but only AFTER attempting the consuming repo's
project-specific consultation (wired in via
`.game-of-cards/hooks/decide-card.md`). `Skill(decide-card)` lowers
the gate back to `none` in one action, which is what makes the line
restart cheap. Status stays `open` so the next `pull-card` claims and
implements per the recorded decision.

The role split (lazy Andon):

```
HUMAN  OR  AGENT-WITH-RUBRIC            AGENT
  decide what to do                        claim from gate=none queue
  record why                               implement
  lower the gate                           commit
```

Humans never wield the wrench; they only resolve the cause the worker
flagged. Agents flag-and-wait when the project-specific rubric can't
resolve the question — but agents that can cite the rubric MAY decide
on their own behalf via this skill. The Andon-cord is now lazy: try
the rubric, then pull. Keeps the human out of the loop when
project-specific reasoning is decisive.

## What this skill does to the card

1. **Body.** If a `## Decision required` section exists, replaces it
   with:

   ```
   ## Decision

   *Resolved YYYY-MM-DD:* <one-line decision>

   *Reasoning:* <one-line why>
   ```

   If absent, appends a fresh `## Decision` section to the end of the
   body.

2. **log.md.** Appends one entry:

   ```
   ## YYYY-MM-DD: decision recorded

   <decision> — <reason>. Gate <prior> → none.
   ```

3. **Frontmatter.** Flips `human_gate: decision` (or `session`) →
   `none`. Status is unchanged (`open` stays `open`).

4. **Refuses** if the gate is already `none` (no decision pending) or
   the title doesn't exist.

## Workflow

1. **Read the card body.** Confirm the decision the user is making
   actually answers the parked question. If the body's `## Decision
   required` enumerates options A/B/C, the user's free-text decision
   should map onto one of them (or explicitly reject all and propose
   D).

   ```bash
   goc show <title>
   ```

2. **Run the CLI.**

   ```bash
   goc decide <title> \
       --decision "<one-line what>" \
       --because "<one-line why>"
   ```

3. **Commit happens automatically.** `goc decide` auto-commits
   the body + log + gate flip with subject `decide: <title> — <decision>`.
   The decision is git-observable to sibling branches immediately —
   no separate commit-helper step needed (the diff is purely
   metadata: `README.md` body + `log.md` entry). Pass `--no-commit`
   only when bundling with adjacent state changes is genuinely
   necessary (rare). See `Skill(advance-card)` Step 5 for the
   multi-branch coordination rationale.

## When an agent invokes this skill (lazy Andon)

`Skill(pull-card)` and `Skill(create-card)` may invoke this skill
*after* consulting the consuming repo's project-specific rubric. The
contract for agent-invoked decisions:

!`cat .game-of-cards/hooks/decide-card.md 2>/dev/null || true`

1. **Cite the rubric.** The `--because` MUST start with a clause
   identifying the rubric consulted and what it returned. The hook
   file above defines the citation form the project expects (e.g.,
   `<rubric-name>: <principle> — <one-line application>`).
2. **Cite the primary source** when the answer rests on literature:
   paper DOI/PMID, textbook chapter (e.g., Knuth Vol 3 §6.4), or
   project-doc section.
3. **No agent-decide for human-judgement questions.** Resource
   allocation, scope splits, deadlines, multi-stakeholder alignment,
   taste calls — these remain human-only. The agent must raise the
   gate.
4. **Default to human when ambiguous.** If the project rubric doesn't
   give a clean answer, the agent raises the gate; doesn't guess.
   Treat the contract as a precondition for autonomy, not a license.

If the agent records a decision that violates this contract (no
rubric citation, or human-judgement question), the human can rewind
via `Skill(advance-card) <title> open` (status stays open, gate stays
none — the body's `## Decision` section can be edited directly or
the gate re-parked manually).

## When NOT to use this skill

- **Card needs implementation, not a decision.** If the question is
  "should we do X?" and the answer is yes/no, this skill is right.
  If the question is "implement X" and you're ready to do the work
  yourself, just do the work — the gate stays raised until pull-card
  is the actor implementing.
- **Decision changes scope.** If your "decision" is actually "scope
  this card differently / split into two / supersede with a
  reframing", use `Skill(advance-card) <title> superseded` and
  `Skill(create-card)` for the replacement instead. `decide-card` is
  for *resolving* the card, not *reshaping* it.
- **Gate is `session`, not `decision`.** Both are valid inputs to
  this skill — but think first: a session-gated card was parked
  because the resolution requires a real-time conversation
  (whiteboarding, paired analysis, multi-stakeholder alignment). If
  you're genuinely capturing the session's outcome, use this skill.
  If you're just shortcutting because the session never happened,
  the right move is to schedule the session, not to invent a
  decision.

## What this skill does NOT do

- Does NOT implement the card. Implementation is `pull-card`'s job
  on the next round, now that the gate is lowered. The decision
  recorded here is the briefing pull-card consumes.
- Does NOT close the card. Closure is `Skill(finish-card)`'s
  DoD-gated contract. A decided card still has a DoD to satisfy.
- Does NOT mutate `status`. The card stays `open` (so `pull-card`
  can claim it via `open → active`).

## Cross-references

- `Skill(scan-deck)` — surfaces parked cards (the triage default)
  and walks the decision queue interactively (the "decisions to
  make" Q&A flow that calls this skill per card).
- `Skill(pull-card)` — the autonomous worker that raises the gate
  when stuck and resumes when this skill lowers it.
- `Skill(advance-card)` — the status state machine. Distinct from
  this skill: gate ≠ status. Use `advance-card` for `open→active`,
  `→blocked`, `→disproved`, `→superseded`. Use `decide-card` for
  `gate ≠ none → none`.
- `Skill(card-schema)` — `human_gate` enum and the body convention
  for `## Decision required` sections.
