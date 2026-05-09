---
title: recommend-autocommit-strongly-when-deck-is-version-controlled
summary: "Tie the autocommit default to whether `.game-of-cards/` is under version control. If the deck is gitignored or lives outside any git repo, autocommit is OFF (nothing to commit to anyway). If the deck is tracked, autocommit is ON by default — strongly recommended but user-configurable, because forcing it would break persona #2 (solo developer, who often wants to review the agent's work before committing). When a tracked-deck user disables autocommit, surface a prominent warning so the trade-off is visible to multi-agent personas where deferred commits cause invisible-deck-state hazards."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: none
advances:
  - support-worktrees-and-multi-agent-deck-sync
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] `goc` detects whether `.game-of-cards/deck/` is tracked (i.e. inside a git repo AND not gitignored)
  - [ ] When deck is tracked: autocommit defaults to ON; existing `auto_commit: false` in `config.yaml` is honored but emits a one-time warning per session naming the trade-off (deferred commits hide claim/progress state from parallel agents)
  - [ ] When deck is untracked (no enclosing git repo, or `.game-of-cards/` is gitignored): autocommit is forced OFF (nothing to commit anyway); no warning needed
  - [ ] The `auto_commit` config key remains user-configurable — the change is the default and the warning when disabled on a tracked deck, not removing the knob
  - [ ] Documented persona trade-off: persona #2 (solo developer) keeps the escape hatch to review before committing; persona #3 (multi-agent coordinator) gets a loud warning if anyone disables autocommit because deferred commits silently break swarm visibility
  - [ ] Interaction with `design-claim-protocol-with-branch-and-author-metadata` clarified: claim metadata commits follow the same default + warning pattern
  - [ ] Interaction with `evaluate-deck-as-separate-repo-or-submodule` clarified: deck-as-separate-repo still defaults to autocommit ON because the deck IS a tracked repo
  - [ ] `uv run goc validate` passes
---

# Recommend autocommit strongly when deck is version-controlled

## Why

Autocommit is currently a config flag the user toggles. With the
multi-agent / worktree / separate-repo workflows in flight, a
disabled autocommit on a tracked deck silently breaks the invariant
that motivates tracking the deck in the first place: claims and
progress become invisible to other participants the moment one of
them defers commits.

But forcing autocommit ON is also wrong. Persona #2 (solo developer)
explicitly wants to review what the agent did before committing —
PERSONAS.md names this directly. Forcing autocommit removes that
review step.

The right rule: **strong default, loud warning, escape hatch
preserved.** When the deck is tracked, autocommit defaults to ON; if
a user sets `auto_commit: false`, a one-time-per-session warning
names the trade-off (deferred commits hide state from parallel
agents). When the deck is untracked, autocommit is forced OFF —
there's nothing to commit anyway.

## Open implementation questions (no longer session-gated)

These are answerable by an agent in the implementation card:

1. **Push semantics.** Does the warning only fire if commits are
   present-but-unpushed? Or is the warning purely about
   `auto_commit: false`? Probably the latter — push is a separate
   concern (some users push manually, that's fine).
2. **Migration.** Existing repos with `auto_commit: false` on
   tracked decks: emit the warning the first time `goc` runs after
   upgrade; otherwise honor the setting.
3. **Merge-conflict surface.** On a busy mainline, autocommit-on
   guarantees deck-file conflicts. This belongs to
   `design-claim-protocol-with-branch-and-author-metadata`, not
   here.

## Cross-references

- `support-worktrees-and-multi-agent-deck-sync` (parent epic)
- `design-claim-protocol-with-branch-and-author-metadata` —
  conflict semantics this card relies on
- `evaluate-deck-as-separate-repo-or-submodule` — separate-repo is
  still tracked, so autocommit still applies

## Decision

*Resolved 2026-05-09:* Autocommit defaults to ON when deck is tracked (OFF when untracked), but stays user-configurable. If a tracked-deck user sets auto_commit: false, emit a one-time-per-session warning naming the trade-off.

*Reasoning:* Forcing mandatory contradicts persona #2 (solo developer wants to review before commit, per PERSONAS.md). The hazard for persona #3 (multi-agent coordinator) is solved by a loud warning rather than removing the knob, preserving both personas.
