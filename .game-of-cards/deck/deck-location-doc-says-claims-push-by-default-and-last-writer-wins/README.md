---
title: deck-location-doc-says-claims-push-by-default-and-last-writer-wins
summary: "UNVERIFIED. DECK_LOCATION.md:44 says goc status active autocommits and pushes and that last-writer-wins resolves a claim race, but claim_push is off by default (engine.py:5369) so a default claim only commits locally, and with claim_push on the first writer wins while the later claimer is refused. The page that defines the claim model therefore tells multi-agent setups the defaults are safe for parallel claiming."
status: active
stage: null
contribution: high
created: "2026-09-28T01:35:19Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py sets up a bare remote with two clones and asserts what `DECK_LOCATION.md:44` claims: a default-config `goc status <title> active` pushes, and a second racing claim is resolved last-writer-wins — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] MECHANICAL: the Same-repo row states the shipped protocol: claims commit locally and push only when `workflow.claim_push: true`; with it set, the later claimer is refused with the racing worker's identity (first writer wins); without it, nothing detects the race
  - [ ] MECHANICAL: drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# The deck-location doc says claims push by default and last-writer-wins

> **UNVERIFIED.** Surfaced by an audit hunter on the docs-vs-code seam on
> 2026-09-28. The filing agent re-read and confirmed the citations. No
> `reproduce.py` was written this round; the falsification recipe is
> below.

## Location

- `DECK_LOCATION.md:44`, the Same-repo row of the configuration table:
  > Git on main. `goc status active` autocommits and pushes; other agents
  > pull before claiming. | A worker that forgets to pull races a stale
  > view of the queue. Last-writer-wins on the file resolves it (per the
  > recorded decision in
  > `design-claim-protocol-with-branch-and-author-metadata`).
- `goc/engine.py:5358-5369`, `claim_push_enabled()`: "Return True when
  workflow.claim_push is set; default off." It returns
  `_coerce_config_bool(workflow.get("claim_push"), default=False)`.
- `goc/engine.py:6128`:
  `if new_status == "active" and claim_push_enabled():`. The push only
  happens behind the opt-in.
- `goc/engine.py:5450`: with the opt-in set, the *later* claimer is
  refused: "claim race — already claimed by {other!r} on
  origin/{branch}."
- `goc/templates/game_of_cards/config.yaml:32-39`: `claim_push: true` is
  commented out, "Off by default to preserve solo workflows where pushes
  are user-driven."

## Hypothesis

The doc that defines the claim model states two things the engine does
not do.

1. **Claims are not pushed by default.** A default-config
   `goc status <title> active` commits locally and stops. The hunter's
   scratch run printed `committed` with no `pushed`, and `git status`
   showed `[ahead 1]`.
2. **Races are not last-writer-wins.** With `claim_push` on, the first
   writer wins and the second is refused with exit 2. With it off,
   nothing detects the race at all.

A reader who sets up several agents on one repo from this page concludes
the defaults are safe for parallel claiming. This deck's own history shows
they are not:
[parallel-agents-double-close-cards-because-claim-protections-are-disabled](../parallel-agents-double-close-cards-because-claim-protections-are-disabled/)
(open) is that failure. `DECK_LOCATION.md` is linked from `README.md` and
`PERSONAS.md`. Another member of
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/).

## Why deferred

The citations are confirmed. The hunter reproduced both halves with a
bare remote and two clones: the default printed `pushed=False`, and with
`claim_push: true` the loser exited 2 and the remote worker stayed
`agent-A`. No `reproduce.py` is committed this round.

## Falsification recipe

1. `git init --bare remote.git`, then clone it twice as A and B, each
   with a `goc install`-ed deck.
2. In A, run `goc status <card> active` under the default config.
3. Check whether `origin/main` moved. If it did, claim (1) holds and the
   hypothesis is disproved for (1).
4. Repeat with `claim_push: true`, claiming from A and then from B. If B
   wins, claim (2) holds.

Surfaced by: general-purpose audit hunter (human-facing docs vs code),
2026-09-28.
