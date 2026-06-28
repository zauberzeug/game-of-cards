---
title: design-claim-protocol-with-branch-and-author-metadata
summary: "Design a claim protocol for multi-human + multi-AI work that keeps the deck-on-main invariant intact. A claim must always land on main (so all participants see it). The data carrier — a `worker` frontmatter field with `who` and `where` — is being implemented separately as `add-worker-field-and-filter-to-cards`. This card now focuses on the remaining policy questions: identity model, conflict semantics on concurrent claims, and closure-on-integration enforcement (a card cannot transition to `done` until the work is integrated to main, not just locally DoD-complete)."
status: done
stage: null
contribution: medium
created: 2026-05-07
closed_at: 2026-05-09
human_gate: none
advances:
  - support-worktrees-and-multi-agent-deck-sync
advanced_by:
  - add-worker-field-and-filter-to-cards
  - parallel-agents-double-close-cards-because-claim-protections-are-disabled
tags: [story, infra]
definition_of_done: |
  - [x] Identity model decided: `worker.who` is a free-form string. Decision + rationale recorded in the `## Decision` section.
  - [x] Conflict semantics specified: last-writer-wins on git push with re-fetch + retry. Documented in the `## Decision` section.
  - [x] Closure-on-integration rule implemented: opt-in via `workflow.closure_on_integration: true` in `.game-of-cards/config.yaml`; when enabled, `goc done` runs `git merge-base --is-ancestor HEAD origin/main` and refuses to close otherwise. (`_enforce_closure_on_integration_or_exit` in `goc/engine.py`, called from `_cmd_done`.)
  - [x] `Skill(pull-card)` / `goc advance --status active` extends its push step with re-fetch + retry on push conflict (per the conflict-semantics decision). Opt-in via `workflow.claim_push: true`; on non-fast-forward push, fetches and rebases, aborts with the racing worker's identity if a rebase conflict reveals a concurrent claim. (`_git_claim_push_with_retry` in `goc/engine.py`, wired into `_cmd_status` for the `active` transition.)
  - [x] Audience preamble (in README, per closed `restructure-comic-as-three-panels-and-add-audience-preamble`) names this protocol as FOR multi-human teams vs. NOT-FOR solo workflows. README's "Who this is for" paragraph differentiates "vibe-coders" / "solo developers" / "multi-agent setups where several agents and humans drain a shared task queue"; PERSONAS.md persona 3 (multi-agent coordinator) cross-links this card explicitly, persona 2 (solo developer) explicitly excludes "multi-agent coordination — they're alone".
  - [x] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
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

## Implementation pointers

With the policy decided (see the `## Decision` section below), the
remaining DoD items are concrete code/doc edits:

- **Closure-on-integration check.** Read `workflow.closure_on_integration`
  from `.game-of-cards/config.yaml` (default `false`). When `true`, the
  `goc done` path (`_cmd_done` in `goc/engine.py`) runs
  `git merge-base --is-ancestor HEAD origin/main` and aborts with a
  clear error if the closing commit is not reachable from
  `origin/main`. Add a config-file knob to the schema documentation.
- **Push retry on claim.** The `active`-transition push in
  `goc advance --status active` (and the `_git_auto_commit` flow
  that backs it) re-fetches and re-applies on push conflict, then
  re-reads the card; if status is now `active` (someone else
  claimed first) abort with "already claimed by &lt;worker.who&gt;"
  and exit non-zero. Bound retries (e.g. one re-fetch).
- **Audience preamble verification.** Open the README's audience
  preamble — the three-panel comic + persona descriptions added by
  `restructure-comic-as-three-panels-and-add-audience-preamble`. Confirm
  the multi-human-team panel calls out this protocol; if not, add a
  sentence pointing at it.

## Cross-references

- `support-worktrees-and-multi-agent-deck-sync` (parent epic)
- `add-worker-field-and-filter-to-cards` (child;
  data carrier for who+where)
- `Skill(pull-card)` flow (current claim implementation)
- `surface-active-cards-in-board` (active) — visibility of current
  claims; benefits from the metadata

## Decision

*Resolved 2026-05-09:* Free-form `worker.who` (deck-as-text consistency); last-writer-wins on claim push with re-fetch+retry; closure-on-integration check is opt-in via `workflow.closure_on_integration: true` in config.yaml, implemented as `git merge-base --is-ancestor HEAD origin/main` at `goc done` time.

*Reasoning:* All three favor the existing lightweight philosophy: free-form identity preserves AI/human symmetry without git-config or registry friction; last-writer-wins is bounded by network round-trip and matches the soft-lock model already in use (lease locking is YAGNI until a real race appears); opt-in integration keeps solo workflows fast-pathed while giving multi-team a single-line opt-in.
