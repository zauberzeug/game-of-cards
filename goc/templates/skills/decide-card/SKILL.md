---
name: decide-card
description: Record a decision (what + why) on a parked card and lower the human gate from decision or session to none. AUTO-INVOKE on "I decided X", "let's go with Y", "approved", or any resolution of a parked card — the human's one-action handoff so pull-card can resume.
argument-hint: <title> --decision "<one-line what>" --because "<one-line why>"
---

## When to invoke

Invoke when the user says "I decided X", "let's go with Y", "the answer is Z", "go ahead with", "approved", or otherwise resolves a parked card. The Andon-cord lowering action — pull-card raises the gate; this skill is the human's one-action handoff so pull-card can resume.

# Decide a card

The Andon-cord loop: `Skill(pull-card)` raises `human_gate`
(`none → decision` / `session`) when it hits a question only a human
can answer; this skill lowers the gate back to `none` in one cheap
action. Status stays `open`, so the next `pull-card` claims and
implements per the recorded decision. Humans resolve the cause;
agents wield the wrench — and an agent that can cite the project
rubric MAY decide on its own behalf (lazy Andon, below).

**Edge cases live in `reference.md`** — a sibling file in this
skill's directory. Read the named section only when the situation
actually applies:

| Situation | `reference.md` section |
|---|---|
| Presenting labeled options via AskUserQuestion | Mirroring labeled options |
| The decision reverses / re-scopes a stated verdict | Re-scope reconciliation |
| An agent recorded a decision it shouldn't have | Rewinding an agent decision |
| Why the cord must be cheap to lower | Rationale |

## What this skill does to the card

1. **Body.** Replaces the `## Decision required` section (or appends
   a fresh `## Decision` section) with:

   ```
   ## Decision

   *Resolved YYYY-MM-DD:* <one-line decision>

   *Reasoning:* <one-line why>
   ```

2. **log.md.** Appends up to two entries, timeline-ordered: first an
   archive of the prior `## Decision required` content (the options
   and trade-offs the README rewrite would otherwise lose), then the
   resolution (`<decision> — <reason>. Gate <prior> → none.`).

3. **Frontmatter.** Flips `human_gate: decision` (or `session`) →
   `none`. Status is unchanged (`open` stays `open`).

4. **Refuses** if the gate is already `none` or the title doesn't
   exist.

## Workflow

1. **Read the card body** (`goc show <title>`). Confirm the decision
   actually answers the parked question: if `## Decision required`
   enumerates options A/B/C, the user's free-text decision should map
   onto one (or explicitly reject all and propose D). When eliciting
   the pick with AskUserQuestion, mirror the body's option labels and
   order verbatim — do not reorder or rephrase (`reference.md`
   § Mirroring labeled options).

2. **Run the CLI.**

   ```bash
   goc decide <title> \
       --decision "<one-line what>" \
       --because "<one-line why>"
   ```

3. **Commit follows repo policy.** `goc decide` honors
   `.game-of-cards/config.yaml` `workflow.auto_commit` (default
   `true`), committing body + log + gate flip as
   `decide: <title> — <decision>`. Override per invocation with
   `--no-commit` / `--commit`.

If the decision **reverses or re-scopes a verdict the card already
states**, `goc decide` only writes the `## Decision` block — every
other surface still asserting the old verdict is now stale. Reconcile
by hand: the `summary:` frontmatter, any `> ⚠` body banner, DoD
wording, and mentions in neighbor cards. The CLI prints a reminder on
re-scope language and `goc validate` flags
`DECISION_CONTRADICTS_VERDICT`. For a true re-scope, prefer
supersede + create over an in-place rewrite. Full checklist:
`reference.md` § Re-scope reconciliation.

## When an agent invokes this skill (lazy Andon)

An agent may decide *on its own* only after consulting the consuming
repo's project-specific rubric:

!`cat .game-of-cards/hooks/decide-card.md 2>/dev/null || true`

1. **Cite the rubric.** `--because` MUST start with a clause naming
   the rubric consulted and what it returned (citation form per the
   hook above).
2. **Cite the primary source** when the answer rests on literature:
   DOI/PMID, textbook chapter, or project-doc section.
3. **No agent-decide for human-judgement questions** — resource
   allocation, scope splits, deadlines, stakeholder alignment, taste
   calls. Raise the gate instead.
4. **Default to human when ambiguous.** If the rubric doesn't give a
   clean answer, raise the gate; don't guess.

A decision recorded in violation of this contract can be rewound —
`reference.md` § Rewinding an agent decision.

## When NOT to use this skill

- **Card needs implementation, not a decision.** If you're ready to
  do the work yourself, just do the work.
- **Decision changes scope.** "Scope this differently / split /
  reframe" is not a resolution — use
  `Skill(advance-card) <title> superseded` +
  `Skill(create-card)` for the replacement.
- **Gate is `session` and the session never happened.** Capturing a
  real session's outcome is valid; shortcutting a session that
  never took place is not — schedule the session instead.

## What this skill does NOT do

- Does NOT implement the card (that's `pull-card`'s next round).
- Does NOT close the card (that's `Skill(finish-card)`'s DoD-gated
  contract).
- Does NOT mutate `status` — the card stays `open`.

## Cross-references

- `reference.md` (this skill's directory) — edge cases routed above.
- `Skill(scan-deck)` — surfaces parked cards; its "decisions to make"
  Q&A calls this skill per card.
- `Skill(advance-card)` — status machine + `waiting_on` overlay; gate
  ≠ status.
- `Skill(card-schema)` — `human_gate` enum and the `## Decision
  required` body convention.
