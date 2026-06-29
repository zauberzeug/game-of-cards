---
title: placeholder-cards-superseded-before-they-are-authored
summary: "An autonomous loop superseded a freshly scaffolded card as a duplicate while it still held the default placeholder DoD and stub body — before it had been authored, because the engine had no notion of an unauthored card. FIXED: `goc new` now stamps a `draft: true` flag (cleared by `goc publish` / `goc status active` / `goc done`); drafts are hidden from the queue/scheduler, refused by terminal transitions (superseded/disproved), and excluded from auto-commit — defense-in-depth so unauthored work cannot be acted on by automation."
status: done
stage: null
contribution: medium
created: "2026-06-28T17:57:27Z"
closed_at: "2026-06-29T05:08:54Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
definition_of_done: |
  - [x] TDD: `goc status <card> {superseded,disproved}` refuses on a draft (exit 2, actionable message) and succeeds once the card is authored + published — `tests/test_draft_guard_and_lifecycle.py`.
  - [x] MECHANICAL: `draft` added to schema `optional_fields` (engine + card-schema copies), `Card.draft` property, `goc new` stamps `draft: true`; documented in the `card-schema` skill (schema-doc parity tests green).
  - [x] TDD: `goc publish` clears the flag and refuses a pure scaffold; `goc status active` / `goc done` auto-clear it — `tests/test_draft_guard_and_lifecycle.py`.
  - [x] TDD: draft cards hidden from the `goc` queue + `card_is_ready`, marked `✎` on the board, surfaced under `--status all` with a `draft` field in `--json` — `tests/test_draft_queue_visibility.py`.
  - [x] TDD: `_git_auto_commit` excludes `draft: true` cards (default-on; `goc new --commit` opts out to avoid a half-edge); external-service caveat documented in `config.yaml` — `tests/test_draft_auto_commit_excluded.py`.
  - [x] PROCESS: plugin mirrors synced + OpenClaw skills re-ported (both `--check` green); full `unittest` suite green (sole failure is the pre-existing macOS BSD-`sed` rebase-guard *setup*, red on pristine `main` too) and `goc validate` clean.
worker: {who: Rodja Trappe, where: main}
---

# placeholder-cards-superseded-before-they-are-authored

> Fixed 2026-06-29 — see `## Resolution`. The defect below is preserved as the motivating context.

## What happened

An autonomous `pull-card` loop superseded a card that had just been created with `goc new` but not
yet authored — it still carried the scaffold's placeholder DoD (`- [ ] (replace with real criteria)`)
and stub body (`(write the design doc here)`). The loop judged it a duplicate of an existing closed
card from the similar title alone (the body was empty, so there was nothing else to judge on), ran
`goc status <card> superseded --by <other>`, and wrote a typed `supersedes`/`superseded_by` edge. The
card was **not** a duplicate; its real (later-written) scope differed materially. Unwinding it
required manually deleting the half-edge on both cards before `goc validate` passed.

## Root cause

Two facts combined:

1. `goc new` itself does **not** auto-commit the scaffold (verified: a fresh `goc new` leaves the card
   directory untracked). So the working tree is correctly "for incomplete work".
2. But a consuming repo with `workflow.auto_commit: true`, or an external periodic auto-commit
   service, **publishes the untracked scaffold immediately** — before the author has filled it in.
   Once committed/visible, any concurrent agent or scheduled loop can act on it, and the dedup path
   would supersede a title-only placeholder as a "duplicate".

The engine had no notion of "this card is still a scaffold / not yet authored", so nothing prevented a
terminal transition (`superseded`, `disproved`) on a card whose DoD and body were still the generated
placeholders. That gap is what the resolution closes.

## Why it matters

Scaffold-then-author is the normal create-card flow (file the card, then write the body and DoD). Any
consumer that auto-commits — common in multi-agent setups, which `auto_commit` exists to serve —
turned that brief window into a race where unauthored work could be silently closed by automation. The
cost was lost work plus half-edge cleanup, and it eroded trust in autonomous loops: you could not
safely scaffold a card and fill it a moment later.

## Decision

*Resolved 2026-06-29T04:06:45Z:* Implement all three as defense-in-depth — A: engine guard rejecting terminal transitions (superseded/disproved) on placeholder cards; B: first-class draft state that queue/dedup/supersede skip; C: auto_commit excludes unauthored placeholder cards.

*Reasoning:* Maintainer call — B's authored/draft flag becomes the shared basis A and C key off (more robust than matching placeholder strings); A also protects legacy decks and non-goc callers, C cuts commit noise from unauthored scaffolds (the stated reason C was added).

## Resolution

A new optional boolean frontmatter field **`draft`** is the single source of truth, an orthogonal
overlay like `waiting_on` (NOT a new `status` enum value — backward-compatible; absent = authored, so
every pre-existing card is unaffected). One predicate, `card_is_draft(card)` (mirroring
`waiting_impedes`), is consulted everywhere so the rule cannot drift per call site.

- **B — draft lifecycle.** `goc new` stamps `draft: true`. The flag clears on `goc status <title>
  active` and `goc done` (claiming or closing proves authorship) and via the new explicit
  `goc publish <title>` verb (which refuses on a pure scaffold — `is_placeholder_scaffold`). Drafts
  are hidden from the default queue, `goc next`, `card_is_ready`, and the scheduler; surfaced only
  under `--status all`; marked `✎` on the board; and carry a `draft` boolean in `--json`. `validate`
  rejects `draft: true` on a terminal card.
- **A — terminal-transition guard.** `goc status <title> {superseded,disproved}` refuses when the
  target is a draft (covering the typed-edge writer on the same path), with a message pointing at
  authoring / `goc publish` / `goc move`.
- **C — auto-commit exclusion.** `_git_auto_commit` filters out `draft: true` cards by default, so an
  unauthored scaffold never reaches shared state through goc. The lone opt-out is `goc new --commit`
  (an explicit user action that must commit the new card with its edge writes atomically — no
  half-edge). External auto-commit services bypass goc and must filter drafts themselves; documented
  in `config.yaml`.

Keyed deliberately on the flag alone, not on a lingering placeholder body: a claimed/closed card has
already cleared the flag and its claim/closure must stay visible and committable.

## Reproduction (now guarded)

1. `goc new sample-card` (scaffold only; do not author) → frontmatter now carries `draft: true`.
2. `goc status sample-card superseded --by some-existing-card` → **refused** (exit 2, "unauthored
   draft scaffold"). Previously this succeeded and wrote a typed edge onto a title-only placeholder.
3. After authoring the card, `goc publish sample-card` (or `goc status sample-card active`) clears the
   flag; the supersede then succeeds normally.
