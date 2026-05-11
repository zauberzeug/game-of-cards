---
title: clarify-agent-unblockable-blocked-cards
summary: Clarify in the GoC skills/schema that `status: blocked` does not imply a human gate. Cards can be blocked by external/upstream conditions while remaining `human_gate: none` when an agent can periodically re-check and unblock them autonomously.
status: active
stage: null
contribution: medium
created: 2026-05-11
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] The relevant GoC skill docs distinguish status/blocking state from human_gate/authority-to-unblock.
  - [ ] At least one skill describes the pattern: `status: blocked` + `human_gate: none` means the card is parked on an agent-checkable external condition.
  - [ ] The docs explain when an autonomous agent may move such a card from `blocked` back to `open` or `active`.
  - [ ] The docs preserve the Andon semantics: `human_gate: decision|session` is only for blockers that require human judgement or a live session.
worker: {who: "claude[bot]", where: main}
---

# Clarify agent-unblockable blocked cards

## Summary

The Game of Cards skills currently explain `status: blocked` and `human_gate`, but the distinction is easy to miss: a card can be blocked without being human-gated.

We should document the pattern explicitly:

```yaml
status: blocked
human_gate: none
```

means:

> The card is parked because work cannot progress right now, but the blocking condition is observable/checkable by an agent. No human decision is required.

## Context / trigger

During an OpenClaw discussion on 2026-05-11, we filed a watcher card for a missing upstream feature: an OpenClaw cross-sandbox artifact bridge. The first draft used:

```yaml
status: blocked
human_gate: session
```

Rodja pointed out that this was semantically wrong. The card did not need a human session; it needed recurring agent research. Correct state:

```yaml
status: blocked
human_gate: none
```

The useful question is:

> What can the KI entblocken?

If the answer is “the agent can periodically check upstream state and proceed when the external condition changes”, the gate should remain `none`.

## Current ambiguity

The existing docs describe:

- `blocked` as parked work
- `human_gate: decision|session` as Andon-cord states for human involvement
- `decide-card` as lowering the gate to `none`

But they do not make the negative case obvious enough:

- `blocked` does **not** automatically mean `human_gate != none`
- a card can be externally blocked but agent-unblockable
- scheduled research/update/watch cards are a valid pattern

## Desired documentation change

Update the GoC skill docs where appropriate, likely:

- `card-schema/SKILL.md` — field semantics for `status` vs `human_gate`
- `advance-card/SKILL.md` — blocked/unblocked transitions and when agents may unblock
- `deck/SKILL.md` — lifecycle/Andon-cord overview
- optionally `pull-card` or `scan-deck` if they describe parked queues

Suggested wording:

> `status` answers “what is the card doing right now?”  
> `human_gate` answers “does progress require a human?”
>
> Use `status: blocked` + `human_gate: none` when a card is waiting on an external condition that agents can observe or re-check: upstream releases, issue/PR movement, CI availability, scheduled research, dependency publication, or another machine-verifiable condition.
>
> Use `human_gate: decision` or `session` only when the unblocker is human judgement, stakeholder alignment, prioritization, or a live discussion.

## Examples

### Agent-unblockable watcher

```yaml
status: blocked
human_gate: none
tags: [documentation]
```

Reason: Watch an upstream GitHub issue weekly. If the PR merges or an API appears, an agent can update the card and move it forward.

### Human-gated decision

```yaml
status: open
human_gate: decision
```

Reason: There are two product directions and a human must choose.

### Human-gated live session

```yaml
status: blocked
human_gate: session
```

Reason: The next step needs a live whiteboard/session with context that cannot be resolved from sources alone.

## Why it matters

Without this distinction, agents may overuse `human_gate: session` for passive observation tasks. That makes the parked queue noisier and routes agent-solvable work back to humans unnecessarily.

Clear semantics let scheduled agents safely maintain watcher cards and only interrupt humans when there is a real decision or relevant change.
