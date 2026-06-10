---
title: parallel-agents-double-close-cards-because-claim-protections-are-disabled
summary: "Two agents independently claimed and closed the same card on diverged clones, producing a merge conflict of two complete solutions. The protections designed for exactly this race — `workflow.claim_push` and `workflow.closure_on_integration` — exist in the engine but are commented out in this repo's own `.game-of-cards/config.yaml`. Decide which to enable for this demonstrably multi-agent repo."
status: open
stage: null
contribution: medium
created: "2026-06-10T03:54:45Z"
closed_at: null
human_gate: decision
advances:
  - design-claim-protocol-with-branch-and-author-metadata
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded in the `## Decision` section — which of `claim_push` / `closure_on_integration` (or both, or neither with rationale) this repo enables.
  - [ ] MECHANICAL: `.game-of-cards/config.yaml` reflects the decision (chosen keys uncommented / explicitly documented as declined).
  - [ ] EMPIRICAL: with the chosen config, `goc status <title> active` on a clone that is behind the remote either propagates the claim or aborts naming the racing worker (exercise the enabled path once and record the output in log.md).
  - [ ] PROCESS: closed root card `design-claim-protocol-with-branch-and-author-metadata` amended with a forward pointer to this card.
  - [ ] EMPIRICAL: `uv run goc validate` passes.
---

# Parallel agents double-close cards because claim protections are disabled

## Location

- `.game-of-cards/config.yaml` — `workflow.claim_push` and
  `workflow.closure_on_integration` both present but commented out.
- `goc/engine.py` — `_git_claim_push_with_retry` (claim propagation with
  re-fetch + retry) and `_enforce_closure_on_integration_or_exit`
  (refuse `done` until HEAD is an ancestor of `origin/main`), both
  implemented and shipped, both opt-in.

## What's broken

The card [codex-plugin-skills-cannot-find-bundled-goc-cli](../codex-plugin-skills-cannot-find-bundled-goc-cli/)
was claimed and closed **twice in parallel** on 2026-06-09: once by a
remote bot (closed 04:29Z, guidance rewrite + regression test) and once
on a local clone (closed 06:49Z, bootstrap-helper infrastructure).
Neither worker saw the other's claim because claims only travel with
ordinary pushes, and neither clone pushed/pulled inside the overlap
window. The result was two complete, divergent solutions and a manual
merge reconciliation (merge commit `5316ebd`).

The closed root card
[design-claim-protocol-with-branch-and-author-metadata](../design-claim-protocol-with-branch-and-author-metadata/)
designed the protocol for exactly this race and landed both enforcement
mechanisms — but left them opt-in to preserve solo workflows, and this
repo's own config never opted in. The dogfood repo is demonstrably a
multi-agent setup (autonomous bot closures on remote main + local human
sessions), i.e. precisely the audience the root card names as FOR.

## Why it matters

Duplicate full implementations are the most expensive form of deck
drift: both workers spend a complete implement-verify-close cycle, and
a human then spends a third cycle reconciling. The deck's scheduler
axis exists to prevent this; an unpropagated claim silently disables
it. Every day the config stays default, the race window stays open for
all ~100 open cards.

## Decision required

Which protections does this repo enable? The two are independent:

1. **`claim_push: true` only** — claims propagate at claim time
   (`goc status <title> active` pushes the claim commit, retries once
   on non-fast-forward, aborts naming the racing worker on conflict).
   Closes the double-claim window. Cost: claiming now requires network
   + push rights; offline claims fail.
2. **`closure_on_integration: true` only** — `goc done` refuses to
   close until HEAD is an ancestor of `origin/main`. Catches the race
   at closure instead of claim time. Cost: changes the current
   user-driven push flow — local closures block until pushed (the
   2026-06-09 local closure would have been refused while main was
   2 commits ahead of origin, unpushed).
3. **Both** — claim-time prevention plus closure-time backstop. The
   root card's design intent for multi-agent setups.
4. **Neither** — accept the race, rely on merge reconciliation.
   Record rationale here so the next incident doesn't re-litigate.

Open sub-question for options 2/3: whether the bot's autonomous loop
always pushes before closing (if not, `closure_on_integration` breaks
the loop until its workflow adds a push step).

## Fix

Once decided: uncomment the chosen key(s) in
`.game-of-cards/config.yaml` under `workflow:`, exercise the enabled
path once (claim from a stale clone, or `goc done` with unpushed HEAD)
and record the observed behavior in `log.md`. Amend the root card's
`log.md` with a forward pointer to this card. No engine changes — both
code paths already ship.
