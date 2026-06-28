---
title: placeholder-cards-superseded-before-they-are-authored
summary: "An autonomous loop superseded a freshly scaffolded card as a duplicate while it still held the default placeholder DoD and stub body — before it had been authored. goc new does not commit the scaffold, but consumers with auto_commit (or an external auto-commit service) publish it immediately, exposing unauthored cards to dedup/supersede automation. The engine has no guard treating a placeholder card as not-yet-real."
status: open
stage: null
contribution: medium
created: "2026-06-28T17:57:27Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [ ] (replace with real criteria once the mechanism is decided)
---

# placeholder-cards-superseded-before-they-are-authored

## What happened

An autonomous `pull-card` loop superseded a card that had just been created with `goc new` but not
yet authored — it still carried the scaffold's placeholder DoD (`- [ ] (replace with real criteria)`)
and stub body (`(write the design doc here)`). The loop judged it a duplicate of an existing closed
card from the similar title alone (the body was empty, so there was nothing else to judge on), ran
`goc status <card> superseded --by <other>`, and wrote a typed `supersedes`/`superseded_by` edge. The
card was **not** a duplicate; its real (later-written) scope differed materially. Unwinding it
required manually deleting the half-edge on both cards before `goc validate` passed.

## Root cause

Two facts combine:

1. `goc new` itself does **not** auto-commit the scaffold (verified: a fresh `goc new` leaves the card
   directory untracked). So the working tree is correctly "for incomplete work".
2. But a consuming repo with `workflow.auto_commit: true`, or an external periodic auto-commit
   service, **publishes the untracked scaffold immediately** — before the author has filled it in.
   Once committed/visible, any concurrent agent or scheduled loop can act on it, and the dedup path
   will supersede a title-only placeholder as a "duplicate".

The engine has no notion of "this card is still a scaffold / not yet authored", so nothing prevents a
terminal transition (`superseded`, `disproved`) on a card whose DoD and body are still the generated
placeholders.

## Why it matters

Scaffold-then-author is the normal create-card flow (file the card, then write the body and DoD). Any
consumer that auto-commits — common in multi-agent setups, which `auto_commit` exists to serve —
turns that brief window into a race where unauthored work can be silently closed by automation. The
cost is lost work plus half-edge cleanup, and it erodes trust in autonomous loops: you cannot safely
scaffold a card and fill it a moment later.

## Decision required

The guard is clear in intent — automation must not treat an unauthored scaffold as a real,
deduplicable card — but the mechanism is a design choice:

- **Option A — engine guard on terminal transitions.** `goc status <card> {superseded,disproved}`
  (and the typed-edge writer) refuses, or hard-warns, when the target card is still a placeholder
  (DoD equals the generated `- [ ] (replace with real criteria)` and/or body equals the
  `(write the design doc here)` stub). Path-independent: protects against any caller, not just the
  loop. Recommended; small and precise.
- **Option B — first-class draft state.** `goc new` marks the card `draft` (or an `authored: false`
  flag); queue/dedup/supersede paths skip drafts; a card leaves draft when it gains a real DoD/body
  (or via an explicit `goc publish`). Bigger surface, but makes "not yet real" explicit everywhere
  and lets `auto_commit` keep committing safely (a committed draft is still skipped).
- **Option C — defer the commit, not the card.** Teach `auto_commit` / the documented auto-commit
  pattern to exclude placeholder cards until authored, so the scaffold never reaches shared state.
  Matches the "working tree is for incomplete work" intent, but only helps consumers that commit
  through goc — an external auto-commit service still needs A or B.

Likely best: **A now** (cheap, robust, protects existing decks), with **B** considered if drafts
warrant first-class modelling. C alone is insufficient because external auto-commit services bypass
goc.

Once chosen, the DoD becomes: a regression test that the selected guard fires on a placeholder card
and does not fire once the card is authored, plus the mechanical change in `goc/engine.py` (and the
schema/skill docs if a draft state is introduced).

## Reproduction sketch

1. `goc new sample-card` (scaffold only; do not author).
2. `goc status sample-card superseded --by some-existing-card`.
3. Observe: the transition succeeds and writes the typed edge, even though `sample-card` is an
   unauthored placeholder. The guard should refuse (Option A) or the card should be skipped as a
   draft (Option B).
