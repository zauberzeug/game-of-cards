---
title: design-claim-protocol-with-branch-and-author-metadata
summary: "Design a claim protocol for multi-human + multi-AI work that keeps the deck-on-main invariant intact. A claim must always land on main (so all participants see it). The data carrier — a `worker` frontmatter field with `who` and `where` — is being implemented separately as `add-worker-field-and-filter-to-cards`. This card now focuses on the remaining policy questions: identity model, conflict semantics on concurrent claims, and closure-on-integration enforcement (a card cannot transition to `done` until the work is integrated to main, not just locally DoD-complete)."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: session
advances:
  - support-multi-branch-and-multi-user-deck-workflows
advanced_by:
  - add-worker-field-and-filter-to-cards
tags: [story, infra]
definition_of_done: |
  - [ ] Identity model decided: is `worker.who` free-form, git-config-derived, or resolved against an explicit registry under `.game-of-cards/`? Decision recorded with rationale
  - [ ] Conflict semantics specified: when two agents try to claim the same card concurrently, the protocol is documented (last-writer-wins on git push with explicit re-fetch + retry loop, or stronger lease-style locking, or something else)
  - [ ] Closure-on-integration rule decided: a card cannot transition to `done` until the work has been integrated to main. Verification mechanism specified — e.g. "the closing commit must be reachable from `origin/main` HEAD at close time" — and implemented in `Skill(finish-card)` / `goc done`
  - [ ] How `Skill(pull-card)` integrates: pull-card already commits + pushes the active transition; this card extends the policy enforced around that
  - [ ] Documented in the audience preamble (per `restructure-comic-as-three-panels-and-add-audience-preamble`) which personas this protocol is FOR (multi-human teams) vs. NOT FOR (solo workflows). Solo workflows can populate `worker` via the child card without needing the closure-on-integration enforcement
  - [ ] `uv run goc validate` passes
---

# Design claim protocol with branch and author metadata

## Why

The current claim flow writes status `active` and pushes — enough
for one human and one agent. When multiple humans + multiple agents
collaborate, the deck and main need to agree on three things beyond
"someone is working on this":

1. **Who** is working on it (so other participants know whom to
   talk to or wait on).
2. **Where** the work lives (so others can check progress without
   asking).
3. **Whether the work is actually integrated** when the card flips
   to `done`. A `done` card whose changes still live on a side
   branch communicates "finished" to participants who cannot yet
   see the change.

The data carrier for (1) and (2) — the `worker` frontmatter
field — is split out into the child card
`add-worker-field-and-filter-to-cards`, which is
gate=none and pullable now. This card is the policy layer that
sits on top.

## Decisions taken

- **Storage:** frontmatter, not a separate file. (Chosen for
  alignment with the rest of card metadata.)
- **Field name:** `worker` (concrete; avoids the linguistic trap
  of `claimee` whose `-ee` suffix actively miscommunicates).
  Accepts a flat string or a nested `{who, where}` mapping.
- **Scope:** field exists on cards in any status, not derived from
  active state. Set at filing time as a designation or capability
  tag (e.g. `worker: gpu-rig` for GPU-required work,
  `worker: human` for cards needing human review). Refined or
  populated on claim with branch context.
- **Persistence:** kept after close as a historical record of who
  worked on the card. Multi-claim history still lives in `log.md`.
- **Filterable:** `goc -v --worker <X>` so autonomous loops on
  specialized runners self-route to eligible cards.

These are now in the child card's DoD. This card no longer
re-litigates them.

## Why still session-gated

Three policy questions remain that benefit from real-time
discussion:

1. **Identity model.** Is `worker.who` a free-form string, the
   git config user, or resolved against an explicit registry under
   `.game-of-cards/`? Each has trade-offs for trust, friction, and
   server-side-agent identification.
2. **Concurrent-claim conflict semantics.** Two agents call
   `goc advance --status active` on the same card seconds apart.
   Last-writer-wins on git push is the cheapest answer; lease-style
   locking is stronger but heavier. Pick.
3. **Closure-on-integration enforcement.** How does `goc done`
   verify that the work is actually merged to main, without
   building a bespoke git introspection layer? Candidate: "the
   closing commit must be reachable from `origin/main` HEAD at
   close time", checked via `git merge-base --is-ancestor`.

## Cross-references

- `support-multi-branch-and-multi-user-deck-workflows` (parent epic)
- `add-worker-field-and-filter-to-cards` (child;
  data carrier for who+where)
- `Skill(pull-card)` flow (current claim implementation)
- `surface-active-cards-in-board` (active) — visibility of current
  claims; benefits from the metadata
