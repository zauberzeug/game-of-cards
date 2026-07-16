---
title: openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution
summary: "The OpenClaw plugin's `resolveDeckDir` (index.ts) reimplements the engine's deck-root resolution but omits three whole behaviors: the git-worktree `worktree_deck: shared` redirect to the primary tree, the canonical-wins dual-tree precedence, and the bounded nearest-ancestor deck walk (added 3e17e3b3, boundary rule 30355095). In a shared-deck worktree the session-start active-card reminder reads the worktree-local (empty) deck and stays silent, so an agent with live cards visible to `goc` is never reminded to resume them. A sixth hand-ported predicate drifting from the engine, beyond the five tracked by the parity meta-fix."
status: open
stage: null
contribution: medium
created: "2026-06-05T05:39:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded in this README (reimplement worktree/dual-tree resolution in TS vs delegate deck-root resolution to the engine) with rationale in log.md — preferably folded into the mechanism chosen by `openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`.
  - [ ] TDD: a regression test exercises `resolveDeckDir` (or its replacement) under Node for a shared-deck worktree layout and asserts it resolves to the primary tree's `.game-of-cards/deck`, matching what `goc.engine._resolve_deck_root` + `_resolve_deck_dir` return for the same layout.
  - [ ] TDD: a regression test asserts canonical-wins precedence — when both `.game-of-cards/deck/` and legacy `deck/` exist, the hook reads `.game-of-cards/deck/` (the engine's choice), not `deck/`.
  - [ ] MECHANICAL: the OpenClaw session-start active-card reminder fires in a shared-deck worktree (no longer silent); `python3 scripts/port_skills_to_openclaw.py --check` and `uv run goc validate` clean.
---

# OpenClaw resolveDeckDir ignores git-worktree shared-deck resolution

## Location

- `openclaw-plugin/index.ts:266-274` — `resolveDeckDir`:

  ```ts
  async function resolveDeckDir(projectDir: string): Promise<string> {
    const primary = resolve(projectDir, ".game-of-cards", "deck");
    try {
      await readdir(primary);
      return primary;
    } catch {
      return resolve(projectDir, "deck");
    }
  }
  ```

- `goc/engine.py:42-120` — the engine's two-stage resolution this is meant to
  mirror:
  - `_detect_worktree_common_root` / `_resolve_deck_root` (lines 42-94): when
    `cwd` is inside a git worktree **and** `worktree_deck: shared` is enabled
    (env `GOC_WORKTREE_DECK=shared`, or `workflow.worktree_deck: shared` in the
    common root's `config.yaml`), the deck root is redirected to the **primary
    working tree root** so every worktree shares one deck.
  - `_resolve_deck_dir` (lines 97-120): canonical-wins precedence — when both
    `.game-of-cards/deck/` and legacy `deck/` exist it returns the **canonical**
    path (and flags `_DUAL_TREE_CONFLICT`); legacy is returned only when
    canonical is absent.

- `openclaw-plugin/index.ts:528` — the sole consumer: `session_start` calls
  `resolveDeckDir(projectDir)` then `findActiveCards(deckDir)` to compose the
  "[GoC] Active card(s) … resume or close before starting new work" reminder.

## What's broken

`resolveDeckDir` is a hand-reimplementation of the engine's deck-root
resolution that drops three whole behaviors:

1. **No worktree shared-deck redirect.** It resolves `.game-of-cards/deck`
   relative to the agent-supplied `projectDir` only. It never runs the
   `git rev-parse --git-dir` / `--git-common-dir` worktree probe, and never
   reads `worktree_deck: shared`. So in a worktree configured for a shared
   deck, the deck physically lives under the *primary* tree, the worktree's own
   `projectDir/.game-of-cards/deck` does **not** exist, `readdir` throws, and
   the hook silently falls back to `projectDir/deck` (also absent) — yielding
   an empty active-card set.

2. **No canonical-wins dual-tree precedence.** It uses `readdir` *success* as
   the selector rather than the engine's existence-precedence, and falls back
   to legacy `deck/` on **any** `readdir` error (ENOENT, ENOTDIR, EACCES), where
   the engine returns canonical whenever canonical exists.

3. **No bounded nearest-ancestor deck walk.** `_resolve_deck_root` now also
   walks from cwd toward the filesystem root and returns the nearest ancestor
   holding `.game-of-cards/` — climbing plain workspace directories but
   stopping before entering a *different* git working tree (commits
   `3e17e3b3` and `30355095`, the latter closing
   [deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in](../deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in/)).
   `resolveDeckDir` never walks at all, so a subdir-of-repo or
   workspace-level deck the engine resolves is invisible to the TS hooks.

The `goc` *tool* in this same plugin is unaffected — it shells out to
`python3 -m goc.cli`, which runs the real engine resolution. Only the
TypeScript lifecycle hooks use `resolveDeckDir`, so the engine and the hooks
disagree about which deck is "the deck" precisely in the worktree-shared-deck
case the engine added support for.

## Why it matters

Reachability path: the repo already supports shared-deck worktrees
(`spike-worktree-auto-resolves-deck-from-main-repo`,
`support-worktrees-and-multi-agent-deck-sync`), and `_resolve_deck_root` is
live engine code that honors `GOC_WORKTREE_DECK=shared` / `worktree_deck:
shared`. An agent working in such a worktree has `status: active` cards that
`goc` lists correctly, but the OpenClaw `session_start` hook reads the empty
worktree-local path and emits **no** reminder. The reminder exists to stop an
agent from starting fresh/duplicate work while a card is already claimed — the
exact failure mode the silent path reintroduces. (Note the symmetry with the
parked active-card reminder this session itself emitted at start: that signal
is the safety net being defeated in the worktree case.)

This is a **sixth** hand-ported engine predicate drifting from its Python
source, beyond the five enumerated by
`openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`
(`parseWaitingUntil` / `isImpeded` / `frontmatterTail` / `stripQuotes` /
opt-out regex). Unlike those — which drift by subtle edge-case bugs — this one
drifts by omitting whole engine behaviors, and it is not covered by the
hand-maintained `isImpeded` matrix test. It is filed as a concrete instance and
as new evidence for that meta-fix.

## Decision required

The fix mechanism is entangled with the parity-mechanism decision pending on
`openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting`:

- **Option A — Reimplement in TS.** Port `_detect_worktree_common_root` +
  `_resolve_deck_root` (two `git rev-parse` calls via the OpenClaw runtime
  command API + a `config.yaml` read) and the canonical-wins precedence into
  `resolveDeckDir`. Faithful, but adds a third independently-drifting predicate
  and more git/config logic to keep in sync.
- **Option B — Delegate to the engine (recommended).** Have the hook ask the
  already-vendored engine where the deck is (e.g. a `goc` query that prints the
  resolved `DECK_DIR`) instead of reimplementing resolution in TS. This removes
  the predicate from the drift surface entirely and is the natural shape if the
  meta-fix lands on "delegate, don't reimplement".

Recommend resolving this **through** the meta-fix's chosen mechanism rather
than independently, so the deck-root predicate is brought under whatever parity
guarantee that card establishes.
