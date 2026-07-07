# decide-card reference — edge cases and rationale

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## Rationale

Lean's **Andon cord** (Toyota production system): when a worker hits
a problem they cannot resolve, they pull the cord; the line stops; a
supervisor walks over, resolves the *cause*, and restarts the line.
The system only works because both pulling AND lowering the cord are
cheap. If lowering took fifteen minutes, workers would route around
the cord and the whole quality system rots.

Our cord is `human_gate`. `Skill(pull-card)` raises it when it hits a
question only a human can answer — but only AFTER attempting the
consuming repo's project-specific consultation (wired in via
`.game-of-cards/hooks/decide-card.md`). `Skill(decide-card)` lowers
the gate back to `none` in one action, which is what makes the line
restart cheap.

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
on their own behalf via this skill. The Andon-cord is lazy: try the
rubric, then pull. Keeps the human out of the loop when
project-specific reasoning is decisive.

## Mirroring labeled options

When the card body's `## Decision required` section enumerates
labeled options (Option A / B / C / D) and you elicit the user's
choice with `AskUserQuestion`, build the picker payload from the
*source's* labels and order:

- **Order:** present the options in the same order the card body
  lists them (A, then B, then C…). Do **not** reorder.
- **Labels:** reuse the card body's option labels verbatim (trimmed
  to `AskUserQuestion`'s length limit if necessary, but keep the
  leading `Option X` token so the user can map their pick back to the
  body).
- **Recommendation:** mark the recommended option *in place* by
  appending ` (Recommended)` to its existing label — leave it where
  it sits in the source order.

This **overrides** the `AskUserQuestion` tool description's "make the
recommended option first" guidance for this bridging case. That
guidance is correct when labels don't pre-exist anywhere; here the
card body is the canonical enumeration, so reordering or rephrasing
forces the user to remap their pick between two presentations (they
read "Option A" in the body, the picker shows it as item #2). The
decision skill exists to make lowering the cord cheap — a picker that
needs a mental remap defeats that purpose.

## Re-scope reconciliation

`goc decide` touches exactly two surfaces: it writes the
`## Decision` block and lowers the gate. That is correct for a
*first* decision — but when the decision **reverses or re-scopes a
verdict the card already states**, every other place still asserting
the old verdict is now stale, and the card contradicts itself. The
stale top-framing (the `summary:`, a body banner) is exactly what the
next agent reads first, so it drives wrong downstream actions.

The CLI helps: when `--decision` contains re-scope/reversal language
(`re-scope`, `supersede`, `reverse`, `overturn`, `no longer`,
`instead of`, `was wrong`, …), `goc decide` prints a reconciliation
reminder listing the surfaces it did NOT update, and `goc validate`
emits an advisory `DECISION_CONTRADICTS_VERDICT` if a re-scoped
decision is left sitting over a still-negative summary/banner. After
recording such a decision, reconcile by hand:

1. **`summary:` frontmatter** — the first thing triage views and
   agents read. Rewrite it to state the *current* verdict.
2. **Body banner / callout** — any `> ⚠ …` line asserting the old
   verdict.
3. **DoD wording** — items phrased around the old verdict.
4. **Neighbor references** — every mention of this card in its
   `advances` / `advanced_by` cards (status tables, member lists).
   These live in *other* card files; `goc decide` cannot see or
   update them.

**Prefer supersede + create for a true re-scope.** If the decision
genuinely reframes the card rather than resolving it, the cleaner
move is `Skill(advance-card) <title> superseded` +
`Skill(create-card)` for the replacement — that records a typed
`superseded_by` / `supersedes` link so a reader landing on the old
card is routed forward, instead of an in-place rewrite a cold reader
must reconcile by eye.

## Rewinding an agent decision

If an agent records a decision that violates the lazy-Andon contract
(no rubric citation, or a human-judgement question), the human can
rewind via `Skill(advance-card) <title> open` — status stays open,
gate stays none; the body's `## Decision` section can be edited
directly or the gate re-parked manually. Treat the contract as a
precondition for autonomy, not a license.
