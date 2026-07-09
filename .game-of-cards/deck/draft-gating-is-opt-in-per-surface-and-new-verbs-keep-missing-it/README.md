---
title: draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it
status: open
stage: null
contribution: medium
created: "2026-07-09T02:03:25Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, meta-fix, api-contract]
draft: true
summary: "card_is_draft gating is opt-in at every call site, and surfaces keep forgetting it: quality-pass audits (and with --llm --yes rewrites) unauthored scaffolds every listing hides, and decide lowers a draft's gate while printing a false 'any agent can now claim this card'. Fourth and fifth instances of the same family — fix the default, not the sites."
definition_of_done: |
  - [ ] PROCESS: decision recorded — inverted default vs validate-time lint vs per-site fixes (see Decision required)
  - [ ] TDD: reproduce.py exits non-zero — quality-pass no longer reports draft scaffolds, and decide on a draft either refuses or stops claiming the card is claimable
  - [ ] TDD: regression test locks the chosen mechanism so the next new surface cannot silently regress it
  - [ ] MECHANICAL: the draft contract note in the schema/skill docs states the chosen default so future verb authors inherit it
---

# draft-gating-is-opt-in-per-surface-and-new-verbs-keep-missing-it

## Location

- `goc/engine.py:4088-4089` (`_cmd_quality_pass`) — the only filter is
  status:

  ```python
  if status_flag != "all":
      cards = [c for c in cards if c.status == status_flag]
  ```

  No `card_is_draft` gate, unlike `filter_cards` (`engine.py:2637`)
  which hides drafts from every listing.

- `goc/engine.py:5951` ff. (`_cmd_decide`) — the only guard is
  `if t.human_gate == "none"`; no draft guard (contrast
  `_cmd_status`'s draft refusal for superseded/disproved at
  `engine.py:5201`). The unconditional next-step at `engine.py:6000`:

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
   where `_apply_verdict_interactive` (`engine.py:4022`) with `--yes`
   would rewrite the `summary`/DoD of — and `goc move` — a card nobody
   has authored yet: exactly the race `draft: true` exists to prevent.
2. **decide unparks a draft into nowhere.** `goc new --gate decision`
   files a draft; a human resolving the gate with `goc decide` is told
   "any agent can now claim this card", but `draft: true` persists, so
   the card stays hidden from the queue, `--ready`, pull-card, and
   next-card until someone separately runs `goc publish`. The decision
   silently unparks nothing.

Five instances of one root cause is a missing default, not five bugs.
Per-site patching demonstrably does not converge — each new surface
reintroduces the leak.

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
