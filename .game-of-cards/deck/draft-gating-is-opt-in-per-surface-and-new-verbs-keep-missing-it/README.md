---
title: draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it
status: open
stage: null
contribution: medium
created: "2026-07-09T02:03:25Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards
  - waiting-filter-surfaces-draft-scaffolds-as-active-impediments
  - ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card
tags: [bug, meta-fix, api-contract]
summary: "card_is_draft gating is opt-in at every call site, and surfaces keep forgetting it: quality-pass audits (and with --llm --yes rewrites) unauthored scaffolds every listing hides, decide lowers a draft's gate while printing a false 'any agent can now claim this card', and validate warns that the DoD placeholder goc new just wrote lacks a method tag. Instances four through six of the same family — fix the default, not the sites."
definition_of_done: |
  - [ ] PROCESS: decision recorded — inverted default vs validate-time lint vs per-site fixes (see Decision required)
  - [ ] TDD: reproduce.py exits non-zero — quality-pass no longer reports draft scaffolds, and decide on a draft either refuses or stops claiming the card is claimable
  - [ ] TDD: regression test locks the chosen mechanism so the next new surface cannot silently regress it
  - [ ] MECHANICAL: the draft contract note in the schema/skill docs states the chosen default so future verb authors inherit it
---

# draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it

## Location

- `goc/engine.py:4375-4376` (`_cmd_quality_pass`) — the only filter is
  status:

  ```python
  if status_flag != "all":
      cards = [c for c in cards if c.status == status_flag]
  ```

  No `card_is_draft` gate, unlike `filter_cards` (`engine.py:2795`)
  which hides drafts from every listing.

- `goc/engine.py:5951` ff. (`_cmd_decide`) — the only guard is
  `if t.human_gate == "none"`; no draft guard (contrast
  `_cmd_status`'s draft refusal for superseded/disproved at
  `engine.py:5563`). The unconditional next-step at `engine.py:6456`:

  ```python
  print("Next: gate lowered to none — any agent can now claim this card. goc to see the queue.")
  ```

## What's broken (the family, not just the instances)

`goc new` stamps `draft: true` so a half-written scaffold is invisible
and protected until authored. But the gate is **opt-in at every call
site**: each verb/view must remember to consult `card_is_draft`.
Three surfaces already forgot and were fixed one at a time —
[goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards](../goc-triage-lists-unauthored-draft-scaffolds-as-parked-cards/),
[waiting-filter-surfaces-draft-scaffolds-as-active-impediments](../waiting-filter-surfaces-draft-scaffolds-as-active-impediments/),
[ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card](../ready-leverage-line-names-draft-scaffolds-as-the-highest-gated-card/)
(all closed). This audit found instances four and five:

1. **quality-pass audits drafts.** Draft scaffolds flow into the
   antipattern/missing-summary report, and into the `--llm` sample,
   where `_apply_verdict_interactive` (`engine.py:4309`) with `--yes`
   would rewrite the `summary`/DoD of — and `goc move` — a card nobody
   has authored yet: exactly the race `draft: true` exists to prevent.
2. **decide unparks a draft into nowhere.** `goc new --gate decision`
   files a draft; a human resolving the gate with `goc decide` is told
   "any agent can now claim this card", but `draft: true` persists, so
   the card stays hidden from the queue, `--ready`, pull-card, and
   next-card until someone separately runs `goc publish`. The decision
   silently unparks nothing.

A later audit pass (2026-08-07) found instance six, which is the
sharpest of the set because the offending text is goc's own:

3. **`goc validate` warns about the placeholder it just wrote.**
   `validate_dod_method_tags` (`engine.py:2364-2390`) exempts terminal
   cards but not drafts, and `goc new`'s generated DoD stub —
   `SCAFFOLD_DOD_PLACEHOLDER = "- [ ] (replace with real criteria)"`
   (`engine.py:2520`) — carries no method tag. So every freshly
   scaffolded card immediately produces
   `WARN UNTAGGED_DOD_ITEM <title>: 1 DoD item(s) lack a method tag …
   [- [ ] (replace with real criteria)]`. The validator's own docstring
   says the warning "only nudges new authorship"; a draft is by
   definition not yet authored, so the nudge fires before there is
   anything to nudge. Reproduced on a two-command scratch deck:
   `goc new fresh-scaffold-card --summary "…"` then `goc validate`.

Six instances of one root cause is a missing default, not six bugs.
Per-site patching demonstrably does not converge — each new surface
reintroduces the leak.

### The cost is now symmetric: un-gating is per-site too (2026-08-11)

The six instances above are all "a surface forgot to exclude drafts".
A closure on
[zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface](../zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface/)
adds the mirror-image cost, which sharpens the mechanism choice rather
than adding a seventh instance of the same shape.

The zero-match queue line reports how many drafts a query is hiding.
Producing that number means asking the counterfactual *"would this card
appear if its draft flag were cleared?"* — and because the gate is
inlined per site, the counterfactual has to be threaded through **every
site separately**, as an opt-in `include_drafts` keyword:

- `filter_cards` (`engine.py:2809`) — added by
  [empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card](../empty-queue-line-reports-a-drained-deck-right-after-goc-new-scaffolds-a-card/)
- `card_is_ready` (`engine.py:2485`) — same commit; readiness drops
  drafts on a second, independent axis
- `live_impeded` (`engine.py:2570`) — a *third* axis, missed by that
  commit and found only when `goc --waiting --status open` reported a
  draft as hidden that publishing would not have revealed

Three keywords, three cards, one predicate. So the inlining is not just
a recall problem for authors writing new surfaces — it also makes the
gate impossible to reason about *counterfactually* without touching
every site again. Any mechanism chosen below should be judged on both
directions: it has to make "exclude drafts" the default AND leave one
place to ask what that default removed.

## Empirical evidence

`uv run python .game-of-cards/deck/draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it/reproduce.py`:

```
queue hides the draft: True; quality-pass audits it anyway: True
decide prints 'any agent can now claim this card': True; draft flag persists: True; card still absent from --ready: True
DEFECT CONFIRMED: quality-pass audits draft scaffolds and decide falsely announces a hidden draft as claimable.
```

## Why it matters

The draft contract is the deck's protection against automation acting
on unauthored state. Every missed gate re-opens it on a new surface:
`quality-pass --llm --yes` (built for unattended runs) mutating a
scaffold mid-authoring, or a human's `goc decide` reporting success
while the card remains invisible to the autonomous queue — the exact
"decided but nothing pulls it" confusion the gate/draft split was
meant to eliminate. The reachability path is the normal filing flow:
every card created by `goc new` passes through the draft state, and
`--gate decision` drafts persist until a human acts.

## Sibling property: the dependency advisory has the same shape

Recorded 2026-07-29 while closing
[`decide-lowers-a-gate-without-surfacing-unclosed-prerequisites`](../decide-lowers-a-gate-without-surfacing-unclosed-prerequisites/).
Not a scope expansion of this card and not re-filed as a fourth
umbrella — context for whoever picks a mechanism below, because the
three options apply verbatim to a second card property.

The dependency advisory (`dependency_advisory` /
`dependency_blockers`) is opt-in per call site exactly like
`card_is_draft`. Three renderers consult it; the by-title verbs did
not, and were fixed one at a time:

- `goc decide` printed nothing about `advanced_by` — just fixed by
  hand, per-site, in `_cmd_decide`.
- `goc status <title> active` — the claim path `Skill(advance-card)`
  prescribes — still prints nothing. Verified 2026-07-29 on a
  two-card temp deck: claiming a card whose `advanced_by` prereq is
  `open` outputs only `child: open → active`.
- `goc show <title>`, the one command every mutating skill mandates
  first, prints the raw `advanced_by` list without any prereq status,
  so a reader learns the edge exists but not that it is live.

So the deck now carries four properties with one shape — draft
gating (this card), query-flag validation
([`query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it`](../query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it/)),
doc-accuracy guards
([`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)),
and the dependency advisory — and three undecided umbrella cards. That
the family keeps growing one umbrella per property is itself the
signal: option 1 or 2 below, if picked, should be picked as the answer
for *card properties consulted per call site*, not for drafts alone.
Option 3 (per-site fixes) is what has been happening by default.

## Decision required

Which mechanism ends the family?

1. **Invert the default.** `load_all_cards()` (or a thin wrapper all
   verbs use) excludes drafts unless the caller passes
   `include_drafts=True`; the few surfaces that legitimately see
   drafts (publish, show, status-claim, validate) opt in explicitly.
   Pro: new surfaces are safe by construction. Con: touches every
   call site once; a surface that forgets to opt *in* now silently
   ignores drafts (the inverse failure, but the safe direction).
2. **Validate-time lint only.** Keep per-site gating, add a
   regression test / validate rule that enumerates verbs and asserts
   draft behavior for each. Pro: no engine refactor. Con: the
   enumeration itself is the thing that keeps going stale.
3. **Per-site fixes only** (quality-pass filter + decide guard +
   corrected message). Pro: smallest diff. Con: sixth instance is a
   matter of time; explicitly rejected by the meta-fix rule unless
   the maintainer prefers it.

Whichever is picked, the two concrete instances above must end up
fixed and regression-tested (see DoD).
