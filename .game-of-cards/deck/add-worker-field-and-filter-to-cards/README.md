---
title: add-worker-field-and-filter-to-cards
summary: "Add an optional `worker` frontmatter field that names WHO should/will/does work on a card — a specific person, a specific machine, or a capability tag (e.g. GPU-equipped runner, human with rendering expertise). The field is editable on cards in any status (set at filing time as designation, refined at claim time with branch context, persists across status changes). Display the field in `goc -v` and `goc --board` views and add a `--worker <X>` filter so autonomous loops on specialized runners can pull only the cards they are qualified for. Resolves the storage-location and field-name questions from `design-claim-protocol-with-branch-and-author-metadata` while expanding scope to capability-based routing."
status: active
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: none
advances:
  - design-claim-protocol-with-branch-and-author-metadata
advanced_by: []
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] Schema (`goc/schema.yaml`) gains an optional `worker` field accepted on cards in ANY status (open, active, blocked, done, disproved, superseded)
  - [ ] Field shape: either a flat string (`worker: gpu-rig`) or a nested mapping (`worker: {who: gpu-rig, where: feature/foo}`). Both forms parse to the same in-memory model; the flat form is sugar for `{who: <value>}`
  - [ ] Semantics documented: `worker.who` is a free-form identifier — a person ("rodja"), a machine ("gpu-rig-3"), or a capability tag ("gpu-required", "rendering-expert"). No registry enforcement; agents and humans agree on conventions out-of-band (registry resolution stays on the parent design card)
  - [ ] At filing time: `goc new <title> --worker <id>` sets the field. Cards filed without `--worker` have no worker designation
  - [ ] At claim time: `goc advance <title> --status active` (and `Skill(pull-card)`) auto-populates `worker.where` from `git rev-parse --abbrev-ref HEAD` and refines/sets `worker.who` from `git config user.name` IF the card has no pre-existing worker. If a worker is already set (designation), the claim respects it and only adds `where`
  - [ ] At close time: `worker` is NOT cleared. The field persists as a record of who worked on the card. (Historical detail of multiple claims still lives in `log.md`.)
  - [ ] CLI override flags on `goc advance`: `--worker-who <id>` and `--worker-where <branch-or-path>` for cases where auto-detection is wrong (agent identity, server-side run that wants to advertise a different branch)
  - [ ] `goc validate` accepts the field on any status; rejects malformed shapes (e.g. mapping without `who`, non-string values)
  - [ ] `goc -v` shows `worker.who` (and `@ where` when set) per card row
  - [ ] `goc --board` includes worker info in card cells
  - [ ] `goc --worker <X>` filter: substring-match (or exact-match — pick) against `worker.who`. Combines with existing filters via AND. Documented in CLI help
  - [ ] `goc triage` and `Skill(next-card)` respect a `GOC_WORKER` env var (or config) so an autonomous loop on a specific runner only sees its eligible cards by default
  - [ ] Existing active card `support-external-game-of-cards-state-location` and any others currently active are migrated by hand to set `worker` correctly; documented in their `log.md`
  - [ ] Schema example, CLAUDE.md / AGENTS.md card-authoring rules updated to describe `worker` semantics and capability-tag conventions
  - [ ] `uv run goc validate` passes
---

# Add worker field and filter to cards

## Why

A `worker` field carrying who/where info is useful in two distinct
phases of a card's life:

1. **At filing time (designation).** Some cards require a specific
   capability — a machine with GPUs, a human with rendering
   expertise, a server-side runner with credentials, a pad-app
   reviewer. Recording that on the card means autonomous loops
   running on different runners can self-route: a GPU runner pulls
   only `worker: gpu-rig` cards; a human reviewer's `next-card`
   surfaces only `worker: human` cards.
2. **At claim time (current bearer).** When a card flips to
   `active`, the field is also the natural place to carry the
   branch / worktree path where the work is happening. Other
   participants see at a glance: "this card is being worked on by
   X on branch Y".

Today the deck has no equivalent. Status `active` tells you
*something* is happening, but not who or where. Tags carry topic,
not capability.

## Why one field, not two

It would be tempting to split into `assignee` (designation) and
`active_by` (current bearer). One field is cleaner because:

- The two roles overlap in practice. A designated worker who picks
  up the card *is* the current bearer; that's the common case.
- A single filter (`--worker X`) works for both phases: the human
  filtering "what's mine" doesn't care whether they're filtered
  pre-claim or post-claim, only that the card is theirs.
- The lifecycle is simple: set at filing or auto-populate on claim;
  refine on claim if no pre-existing value; persist after close as
  historical record.

The cost is a slight context-dependence: when reading a card,
`worker` means designation if status is open and current bearer if
status is active. The `where` sub-field disambiguates (only set
when actively claimed).

## Why gate=none

The earlier session-gated framing on the parent
(`design-claim-protocol-with-branch-and-author-metadata`) had
several open governance questions. The user has now decided:

- Field name: `worker` (concrete, English, no -ee/-ant trap)
- Storage: frontmatter (not separate file)
- Scope: any status (not derived from active)
- Persistence: kept on close (not cleared)

What remains on the parent (still session-gated) is policy on
identity registry (do we enforce that `worker.who` matches a known
list?) and closure-on-integration enforcement. Neither blocks
shipping the field itself.

## Capability vocabulary

The field accepts free-form strings; conventions emerge in use:

| Example | Meaning |
|---|---|
| `worker: rodja` | Specific person |
| `worker: gpu-rig-3` | Specific machine |
| `worker: gpu-required` | Capability tag — any GPU-equipped runner can claim |
| `worker: human` | Capability tag — needs a human, not an autonomous agent |
| `worker: rendering-expert` | Capability tag — needs domain expertise |

A future card may add a registry under `.game-of-cards/workers.yaml`
to enumerate known workers + their capability tags, but that is
explicitly out of scope here.

## Cross-references

- `design-claim-protocol-with-branch-and-author-metadata` —
  parent design card; remaining policy questions live there
- `emit-advances-and-advanced-by-as-block-style-yaml-lists` —
  block-style YAML pairs naturally with the nested `worker`
  mapping; both serve multi-agent friction reduction
- `surface-active-cards-in-board` (active) — the visibility
  surface that benefits from `worker` data
- `Skill(pull-card)` — current claim trigger; gains the auto-
  populate path AND the worker-filter path
- `Skill(next-card)` — gains worker-aware default filtering
