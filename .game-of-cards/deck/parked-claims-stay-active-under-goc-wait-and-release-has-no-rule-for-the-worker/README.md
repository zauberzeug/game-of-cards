---
title: parked-claims-stay-active-under-goc-wait-and-release-has-no-rule-for-the-worker
summary: "goc wait on an active card leaves the claim active under a waiting_on overlay, and every release path (goc status open, goc decide) keeps worker, so an abandoned claim and a pre-assignment look the same. PR #11 proposed releasing the claim on goc wait (with --keep-claim), clearing worker on re-queue and requiring worker on active cards, but clearing deletes pre-assignments such as worker: gpu-required (measured). The release rules need a decision before any of it is implemented."
status: open
stage: null
contribution: medium
created: "2026-10-22T05:19:23Z"
closed_at: null
human_gate: decision
advances:
  - active-state-conflates-being-worked-on-with-parked-at-human-gate
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: the three questions under `## Decision required` are answered via `Skill(decide-card)` (release on `goc wait`, what a release does to `worker`, whether `goc validate` requires `worker` on active cards)
  - [ ] TDD: regression tests pin the decided behavior for `goc status <title> open`, `goc decide` and `goc wait` on an active card, including a pre-assigned `worker` (e.g. `gpu-required`) surviving or being cleared exactly as decided, and `goc --worker <X>` still finding a pre-assigned card if it survives
  - [ ] MECHANICAL: `advance-card`, `card-schema`, `decide-card` and AGENTS.md describe the decided release rules; plugin mirrors synced and the OpenClaw skills re-ported
  - [ ] PROCESS: `uv run goc validate` passes
---

# Parked claims stay active under `goc wait`, and release has no rule for the worker

## Location

- `goc/engine.py` — `_cmd_wait`: setting an overlay on an `active` card
  leaves `status: active` and `worker` as they are, so the CLI produces
  the `active` + `waiting_on` shape.
- `goc/engine.py` — `_cmd_status`: `goc status <title> open` changes only
  `status`; `worker` stays.
- `goc/engine.py` — `_cmd_decide` (`releases_claim`): a card parked while
  active returns to `open` with its `worker` kept, documented "as
  `goc status <title> open` keeps it"
  ([deciding-a-card-parked-while-active-strands-it-outside-the-pull-queue](../deciding-a-card-parked-while-active-strands-it-outside-the-pull-queue/)).

## What's unresolved

`worker` carries two meanings the engine cannot tell apart: a
**pre-assignment** ("who should work this", e.g. `worker: gpu-required`
or `human`, set by `goc new --worker` or by hand) and a **claim stamp**
("who works it now", written by `goc status <title> active`). A claim
on a pre-assigned card keeps the designation and only adds `where`, so
after the claim both meanings live in one value.

Two lifecycle questions follow from that, and the deck has never
decided them:

1. **Should parking a claim release it?** `goc wait` on an active card
   keeps it active. If the worker never comes back, the card sits
   `active` + `waiting_on` with a live-looking claim that no `--ready`
   queue lists — the abandoned-claim shape.
2. **What does a release do to `worker`?** Keeping it (today) leaves an
   `open` card that still names its last claimer. Clearing it
   (PR #11's proposal) loses the pre-assignment.

## Evidence

PR #11 (claim release lifecycle) implemented: `goc status <title> open`
clears `worker`; `goc wait` on an active card re-queues it to `open` and
clears `worker` unless `--keep-claim`; `goc validate` requires `worker`
on every active card. A probe against that branch merged with main, on a
temp deck whose card was pre-assigned `worker: gpu-required`:

```
claim:   probe: open → active   ->  status: active, worker: {who: gpu-required, where: main}
release: probe: active → open   ->  status: open   (worker line gone)
goc --worker gpu-required --status all  ->  No cards match (status: all; worker: 'gpu-required').
wait:    ... active claim released to open   ->  status: open   (worker line gone)
```

The same probe on main keeps `worker: {who: gpu-required, where: main}`
after the release, and `goc wait` leaves the card `active` with its
worker. So the proposal fixes the abandoned-claim shape by destroying
the documented "who should work this" use (AGENTS.md § `worker` field).

The PR's third change, `goc validate` requiring `worker` on active
cards, would turn consumer decks red after an upgrade wherever a legacy
active card has no worker — claims made before
[claims-without-a-git-identity-leave-active-cards-no-one-is-named-for](../claims-without-a-git-identity-leave-active-cards-no-one-is-named-for/)
in an environment without a git identity left exactly that shape.

## Decision required

1. **Release on `goc wait`?**
   - **Keep the claim.** Today's behavior; `active` + `waiting_on` stays a
     CLI-producible shape and the session-start / triage views must keep
     handling it.
   - **Release by default.** `goc wait` on an active card re-queues it to
     `open`; `--keep-claim` opts out for a worker that stays across a
     bounded wait.
2. **What does a release (`status open`, `decide`, a releasing `wait`) do
   to `worker`?**
   - **Keep it.** Today's behavior, consistent across all release paths;
     an open card may still name its last claimer.
   - **Clear it.** PR #11's rule; loses pre-assignments (measured above).
   - **Clear only the claim stamp.** Record what the claim added (e.g.
     keep the pre-assigned `who` and drop only the claim's `where`, or
     record claim provenance) so a pre-assignment survives the release.
3. **Should `goc validate` require `worker` on active cards?**
   - **No.** Today's behavior.
   - **Yes, as a warning first.** Surface legacy worker-less active cards
     without turning decks red, then promote to an error in a later
     release.
   - **Yes, as an error.** PR #11's rule.

## Related

- [active-state-conflates-being-worked-on-with-parked-at-human-gate](../active-state-conflates-being-worked-on-with-parked-at-human-gate/)
  — the meta-card on what `active` means; this card's answer to question 1
  feeds it.
- [session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone](../session-start-hook-says-resume-active-cards-that-pull-card-says-to-leave-alone/)
  and
  [escalate-repeatedly-auto-released-cards-without-an-attempt-counter](../escalate-repeatedly-auto-released-cards-without-an-attempt-counter/)
  — neighbors on the same claim lifecycle.
- A worker killed mid-flight (timeout, SIGKILL) still leaves `active`
  behind under every option here, because nothing writes when a process
  dies; releasing that class needs a time bound (a claim timestamp plus
  an expiry the queue reads), not a writer.
