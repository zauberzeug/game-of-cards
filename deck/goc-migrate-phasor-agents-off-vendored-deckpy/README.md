---
title: goc-migrate-phasor-agents-off-vendored-deckpy
summary: "phasor-agents currently vendors `.claude/skills/deck/deck.py` plus the 11 skill directories — the in-repo engine is the source of truth. Once `game-of-cards` ships on PyPI, this repo eats its own dogfood: delete the vendored `deck.py`, update skills to shell to the bootstrap wrapper (`_goc-bootstrap.sh`) which routes to PATH-resolved `goc`. The decision this card carries is the cutover timing: immediately on v1 release (highest faith in the new CLI; risk of breaking active pong work if there's a regression), or run vendored + PyPI in parallel for a release cycle (safer; doubles maintenance for one cycle). This is the canonical 'eat your own dogfood' integration test for the whole epic — if it works on phasor-agents (with ~120 cards, 99 open, active /loop work), it works anywhere."
status: open
stage: null
contribution: medium
created: 2026-05-03
closed_at: null
human_gate: none
advances: [goc-ship-game-of-cards-as-cross-agent-cli]
advanced_by: []
tags: [story, infra, meta-fix]
definition_of_done: |
  - [ ] Decision recorded: cutover timing (immediate-on-v1 vs parallel-then-cut) with rationale
  - [ ] Vendored `.claude/skills/deck/deck.py` removed from this repo (or, in the parallel case, marked deprecated with a comment header pointing at PyPI)
  - [ ] All 11 skill SKILL.md files in this repo route through the bootstrap wrapper (`_goc-bootstrap.sh`) — same code path every external consumer uses
  - [ ] Pre-commit hook switched from `uv run python .claude/skills/deck/deck.py validate` to `goc validate` (via wrapper)
  - [ ] `Skill(use-game-of-cards)` is either deleted (superseded by `goc install` / `goc upgrade`) or kept as a redirect skill that runs `goc upgrade --check` and `goc install`
  - [ ] Full pong test suite (regression + active /loop work) green after migration; no regressions on /find-bug, /fix-bug, /pull-card cycles
  - [ ] Schema version pinned in `deck/.goc-version`; `goc validate` confirms repo schema matches
  - [ ] CLAUDE.md updated to reference `goc <verb>` instead of `uv run python .claude/skills/deck/deck.py <verb>` throughout (the existing references become outdated post-migration)
---

# Migrate phasor-agents off vendored `deck.py`

## Why

Sub-card of `goc-ship-game-of-cards-as-cross-agent-cli`. This is the **dogfood card** — the one that proves the whole epic works in production by running it on the most demanding GoC repo there is (this one).

Today phasor-agents has the engine vendored: `.claude/skills/deck/deck.py` plus the 11 skill directories live in this repo's git tree. Every CLAUDE.md reference to "the deck CLI" actually means `uv run python .claude/skills/deck/deck.py`. The methodology evolves *here*; downstream consumers via `Skill(use-game-of-cards)` get a snapshot.

Once `goc` ships on PyPI, that asymmetry is wrong: this repo should be the *first consumer*, not a privileged source. If `goc install` doesn't work cleanly on a repo with 120 cards, an active /loop, eight feedback memories about loop-stash interactions, and live pong work, then it doesn't work — and we should find out before any downstream user does.

## Decision

*Resolved 2026-05-03:* Immediate cutover on v1 release

*Reasoning:* real dogfood is the only meaningful integration test and vendored-during-transition will drift in subtle ways
## Recommendation (for the human deciding)

**Option C** is probably right. The cost of cherry-picking a week of pong work onto a validation branch is real but bounded; the cost of Option A's regression-during-active-pong is unbounded. Option B's parallel maintenance is the worst of both worlds — the vendored copy will drift and someone will discover a divergence at exactly the wrong moment.

## What

After the decision lands:

1. **Delete vendored engine** — remove `.claude/skills/deck/deck.py` and the engine library directories.
2. **Install the bootstrap wrapper** — `goc install` (or manual placement) drops `.claude/skills/_goc-bootstrap.sh`.
3. **Rewrite skill invocations** — every `uv run python .claude/skills/deck/deck.py` in skill SKILL.md files becomes `.claude/skills/_goc-bootstrap.sh` (which routes to `goc`).
4. **Pre-commit hook** — `.pre-commit-config.yaml`'s deck validator entry switches to `goc validate`.
5. **CLAUDE.md** — update all references that say "run the CLI under `.claude/skills/deck/deck.py`" to say `goc <verb>`.
6. **`Skill(use-game-of-cards)` resolution** — either delete (superseded) or convert to a thin wrapper that runs `goc install` / `goc upgrade --check`. Decide in the same PR.
7. **Full validation pass** — pytest, /loop dry run, /find-bug + /fix-bug round, manual scan-deck, decide-card cycle, kanban-board view all green.

## Cross-references

- Parent epic: `goc-ship-game-of-cards-as-cross-agent-cli`
- Depends on: sub-cards 1 (PyPI release), 2 (`goc install`), 5 (bootstrap wrapper) all done
- Existing prior art: `Skill(use-game-of-cards)` mode A (the in-repo scaffolder this card supersedes for at-scale consumers)
