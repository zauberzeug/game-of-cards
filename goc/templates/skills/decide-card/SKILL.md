---
name: decide-card
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

2. **log.md.** Appends up to two entries — the archive precedes the
   resolution so the journal reads as a timeline (filed → decided):

   - **If the body had a `## Decision required` section**, first archives
     its prior content (the options, recommendation, and trade-offs that
     are about to be overwritten in the README) as a dated entry stamped
     with the card's `created` timestamp:

     ```
     ## <created>: decision deliberation archived

     Archived from the README's `## Decision required` section … 

     <prior section content — options, recommendation, trade-offs>
     ```

     README is the dashboard (rewritten in place); log.md is the journal
     (append-only). The archive recovers the deliberation that the README
     replacement would otherwise lose.

   - Then records the resolution:

     ```
     ## <decided-at>: decision recorded

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

   **1.5. Eliciting the pick from labeled options — mirror the source
   verbatim.** When the card body's `## Decision required` section
   enumerates labeled options (Option A / B / C / D) and you elicit the
   user's choice with `AskUserQuestion`, build the picker payload from
   the *source's* labels and order:

   - **Order:** present the options in the same order the card body
     lists them (A, then B, then C…). Do **not** reorder.
   - **Labels:** reuse the card body's option labels verbatim (trimmed
     to `AskUserQuestion`'s length limit if necessary, but keep the
     leading `Option X` token so the user can map their pick back to
     the body).
   - **Recommendation:** mark the recommended option *in place* by
     appending ` (Recommended)` to its existing label — leave it where
     it sits in the source order.

   This **overrides** the `AskUserQuestion` tool description's "make
   the recommended option first" guidance for this bridging case. That
   guidance is correct when labels don't pre-exist anywhere; here the
   card body is the canonical enumeration, so reordering or rephrasing
   forces the user to remap their pick between two presentations (they
   read "Option A" in the body, the picker shows it as item #2). The
   decision skill exists to make lowering the cord cheap — a picker
   that needs a mental remap defeats that purpose.

2. **Run the CLI.**

   ```bash
   goc decide <title> \
       --decision "<one-line what>" \
       --because "<one-line why>"
   ```

3. **Commit follows repo policy.** `goc decide` reads
   `.game-of-cards/config.yaml` `workflow.auto_commit` (default: `true`)
   before committing the body + log + gate flip with subject
   `decide: <title> — <decision>`. Pass `--no-commit` to skip for one
   invocation, or `--commit` to force a state-only commit when the repo
   config disables automatic commits. See `Skill(advance-card)` Step 5
   for the multi-branch coordination rationale.

## Reconcile a re-scope (decide updates only two things)

`goc decide` touches exactly two surfaces: it writes the `## Decision`
block and lowers the gate. It does **not** rewrite anything else on the
card. That is correct for a *first* decision — but when your decision
**reverses or re-scopes a verdict the card already states**, every other
place that still asserts the old verdict is now stale, and the card
contradicts itself. The stale top-framing (the `summary:`, a body banner)
is exactly what the next agent reads first, so it drives wrong downstream
actions.

The CLI helps: when `--decision` contains re-scope/reversal language
(`re-scope`, `supersede`, `reverse`, `overturn`, `no longer`, `instead
of`, `was wrong`, …), `goc decide` prints a reconciliation reminder
listing the surfaces it did NOT update (and `goc validate` emits an
advisory `DECISION_CONTRADICTS_VERDICT` if a re-scoped decision is left
sitting over a still-negative summary/banner). After recording such a
decision, reconcile by hand:

1. **`summary:` frontmatter** — the first thing triage views and agents
   read. Rewrite it to state the *current* verdict.
2. **Body banner / callout** — any `> ⚠ …` line asserting the old verdict.
3. **DoD wording** — items phrased around the old verdict.
4. **Neighbor references** — every mention of this card in its
   `advances` / `advanced_by` cards (status tables, member lists). These
   live in *other* card files; `goc decide` cannot see or update them.

**Prefer supersede + create for a true re-scope.** If the decision
genuinely reframes the card rather than resolving it, the cleaner move is
`Skill(advance-card) <title> superseded` + `Skill(create-card)` for the
replacement — that records a typed `superseded_by` / `supersedes` link so
a reader landing on the old card is routed forward, instead of an
in-place rewrite a cold reader must reconcile by eye. See "When NOT to
use this skill → Decision changes scope" below.

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
- `Skill(advance-card)` — the status state machine + `waiting_on`
  overlay. Distinct from this skill: gate ≠ status. Use `advance-card`
  for `open→active`, `→disproved`, `→superseded`, and `goc wait`.
  Use `decide-card` for `gate ≠ none → none`.
- `Skill(card-schema)` — `human_gate` enum and the body convention
  for `## Decision required` sections.
