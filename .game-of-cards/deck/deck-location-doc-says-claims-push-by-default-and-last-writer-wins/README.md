---
title: deck-location-doc-says-claims-push-by-default-and-last-writer-wins
summary: "DECK_LOCATION.md said goc status active autocommits and pushes and that last-writer-wins resolves a claim race. reproduce.py showed that a default claim only commits locally, so nothing detects a racing claim, and that with workflow.claim_push on the first writer wins while the later claimer exits 2. The Same-repo claim row now states that protocol, including the open identical-claim hole, the Offline row excepts claim_push, and tests/test_deck_location_claim_rows.py runs the protocol on scratch remotes and checks both rows both ways."
status: done
stage: null
contribution: high
created: "2026-09-28T01:35:19Z"
closed_at: "2026-10-04T06:19:43Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py sets up a bare remote with two clones and asserts what `DECK_LOCATION.md:44` claims: a default-config `goc status <title> active` pushes, and a second racing claim is resolved last-writer-wins — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] MECHANICAL: the Same-repo row states the shipped protocol: claims commit locally and push only when `workflow.claim_push: true`; with it set, the later claimer is refused with the racing worker's identity (first writer wins); without it, nothing detects the race
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands
  - [x] MECHANICAL: the Offline row of the same page excepts `workflow.claim_push`, under which an offline claim commits locally but `goc status` exits 2
  - [x] TDD: `tests/test_deck_location_claim_rows.py` checks both rows against the protocol run on scratch remotes, fires every check on the pre-fix wording, and fires every check on the current wording when each observation is flipped
worker: {who: "claude[bot]", where: main}
---

# The deck-location doc said claims push by default and last-writer-wins

## What was broken

`DECK_LOCATION.md` defines the claim model for the one deck location GoC
ships. Its Same-repo row in "Claim and sync semantics" said:

> Git on main. `goc status active` autocommits and pushes; other agents pull
> before claiming. | A worker that forgets to pull races a stale view of the
> queue. Last-writer-wins on the file resolves it (per the recorded decision in
> `design-claim-protocol-with-branch-and-author-metadata`).

Both halves were wrong:

1. **Claims do not push by default.** `claim_push_enabled()`
   (`goc/engine.py:5405`) defaults to off, and the shipped
   `goc/templates/game_of_cards/config.yaml` leaves `claim_push: true`
   commented out. A default claim commits locally and stops, and a second
   claimer on another clone succeeds too. Nothing detects the race.
2. **The race is not last-writer-wins.** With `claim_push: true`,
   `_git_claim_push_with_retry` (`goc/engine.py:5420`) pushes the claim. A
   stale claimer's push is rejected, it rebases, the rebase conflicts on the
   card's `worker` line, and `goc status` exits 2 with "claim race — already
   claimed by 'agent-A'". The first claim stays. The cited decision does say
   "last-writer-wins", but the same card's DoD implemented the reverse, so the
   row was faithful to a decision record that was wrong from the day it was
   written.

The Offline row of the same page ("Fully functional. Git push deferred") was
wrong for the same opt-in. With `claim_push: true` and no reachable remote, the
claim still commits locally, but `goc status` exits 2 ("push failed and fetch
failed"). That matters to `Skill(pull-card)`, which reads exit 2 as a claim that
did not stick.

A reader setting up several agents from this page would conclude the defaults
make parallel claiming safe. This deck already holds the failure that follows:
[parallel-agents-double-close-cards-because-claim-protections-are-disabled](../parallel-agents-double-close-cards-because-claim-protections-are-disabled/).

## What changed

- `DECK_LOCATION.md`, Same-repo row of "Claim and sync semantics". A claim
  commits locally and pushes only when `workflow.claim_push: true` is set (off
  by default). With it set, the first writer wins: the later claimer is refused
  with exit 2, naming the racing worker. A claim that writes the same `worker`
  as the remote one reports success instead; the row links the open,
  decision-gated
  [claim-push-reports-success-when-rebase-drops-identical-racing-claim](../claim-push-reports-success-when-rebase-drops-identical-racing-claim/).
  Without `claim_push`, nothing detects the race.
- `DECK_LOCATION.md`, Same-repo row of "Offline behavior": the `claim_push`
  exception.
- `tests/test_deck_location_claim_rows.py` (new). It runs the protocol on
  scratch bare remotes with the shipped config template, in four setups:
  default, `claim_push` with distinct identities, `claim_push` with one shared
  identity, and `claim_push` offline. It then checks both rows against what
  happened. Every check runs both ways, so the guard turns red when the engine
  moves as well as when the page does. In particular, once the identical-claim
  card's decision lands and the engine refuses that claim, the row's link to the
  card has to go.
- The closed
  [design-claim-protocol-with-branch-and-author-metadata](../design-claim-protocol-with-branch-and-author-metadata/)
  carries a one-line forward pointer and a post-close amendment. Its Decision's
  "last-writer-wins" names the reverse of what it shipped.

Not changed here: `ABOUT.md` and the shipped deck skill repeat the same
reassurance ("git's merge handles the claim race"). They are three files plus
six mirrors, so they were filed separately as
[deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects](../deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects/).

## Evidence

`uv run python .game-of-cards/deck/deck-location-doc-says-claims-push-by-default-and-last-writer-wins/reproduce.py [DOC]`
observes the protocol and checks the page given (default: the working tree's).

Against the pre-fix page (`git show 8c7a4053:DECK_LOCATION.md`, the claim commit), exit 1:

```
Observed:
  default config: claim pushed to the remote: False
    agent-A: exit 0, stdout ends '  committed'
    agent-B (stale): exit 0, stderr ''
  default config: racing claim detected: False
  claim_push: claim pushed to the remote: True
    agent-B (stale): exit 2, stderr "ERROR: race-card: claim race — already claimed by 'agent-A' on origin/main. Your local claim commit is unpushed; reset to origin/main and pull a different card."
    remote card after both claims: {'status': 'active', 'worker': '{who: agent-A, where: main}'}
  claim_push: winner = first writer; loser refused naming the winner: True
  claim_push, one identity: second claim exit 0, stdout ends '  pushed (after rebase)'
  claim_push, offline: exit 2, claim committed locally: True, stderr starts "push failed and fetch failed: fatal: '…/offline/unreachable.git' does not appear to be a git repository"

5 claim(s) contradicted:
  - says goc pushes the claim, but a default claim does not push: '`goc status active` autocommits and pushes;'
  - does not say the first writer wins, but with claim_push the later claimer is refused
  - never says that under the default config nothing detects a racing claim
  - omits that an identical claim (one shared worker identity) reports success under claim_push
  - Offline row says the push is deferred, but an offline claim_push claim exits non-zero
```

Against the fixed page, the same observations and exit 0: "Both rows match the
observed claim protocol."
