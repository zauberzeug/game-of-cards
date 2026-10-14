---
title: python-hooks-ignore-git-worktree-shared-deck-resolution
summary: "The Python SessionStart and Stop hooks found the deck with a copy of the engine's upward walk but not its worktree_deck: shared redirect, so in a linked worktree of a shared-deck repo they read the worktree's own checkout instead of the deck goc uses: the session-start reminder stayed silent about active cards goc lists, and the Stop hook read the checkout's config. Both hooks now run the engine's redirect before the walk (GOC_WORKTREE_DECK, then workflow.worktree_deck in the primary tree's config), pinned to the engine over a linked worktree and 19 config shapes."
status: done
stage: null
contribution: medium
created: "2026-10-05T01:32:49Z"
closed_at: "2026-10-14T05:03:09Z"
human_gate: none
advances:
  - session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: a reproduce.py builds a primary repo with `workflow.worktree_deck: shared`, adds a linked worktree, claims a card from it with `goc`, and asserts `deck_session_start.py` run with `cwd` = the linked worktree names that card — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: `tests/test_project_root_from_subdirectory.py` gains a shared-deck worktree layout, so the hook-versus-engine agreement test covers the redirect and not only the walk
  - [x] MECHANICAL: both Python hooks resolve the shared deck the way `goc.engine._resolve_deck_root` does (env var and common-root config), and their docstrings stop calling the walk alone a mirror of `_resolve_deck_root`; mirrors re-synced; drop the `unverified` tag once reproduce.py lands
  - [x] PROCESS: connected to `session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting` and cross-linked with `openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution`
  - [x] TDD: the hooks' own `workflow.worktree_deck` reader is pinned to `engine._shared_worktree_deck_root` over 19 config texts (`test_hook_config_reading_agrees_with_the_engine`), and both hook scripts, run as subprocesses from inside a shared-deck worktree, name the card `goc` claimed there and read the primary tree's Stop-hook opt-in
worker: {who: "claude[bot]", where: main}
---

# Python hooks ignore git-worktree shared-deck resolution

## What was broken

`goc` resolves its deck in two stages (`goc/engine.py:106-121`,
`_resolve_project_roots`). First, in a linked git worktree whose repo opted
into a shared deck — `GOC_WORKTREE_DECK=shared`, or `workflow.worktree_deck:
shared` in the primary tree's `.game-of-cards/config.yaml`
(`_shared_worktree_deck_root`, `:72-89`) — the deck root is the primary
working tree. Only otherwise does it walk up to the nearest ancestor holding
`.game-of-cards/`. The kickoff reference promises exactly this: set
`worktree_deck: shared` "to make all linked worktrees share the deck in the
primary working tree."

The two Python hooks (`goc/templates/hooks/deck_session_start.py` and
`pattern_generalization_check.py`) cannot import the package, so each carries
its own `_find_project_dir`.
`goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there`
(closed) gave them a copy of the walk but not of the redirect before it, and
their docstrings called the walk alone "a mirror of the walk in
`goc.engine._resolve_deck_root`". In a linked worktree of a repo that tracks
`.game-of-cards/`, the walk stops at the worktree's own checkout: a copy of the
deck at that branch's commit, while `goc` reads and writes the primary tree's.

- **SessionStart:** the reminder never named the cards claimed in the shared
  deck, so an agent opening a session in another worktree was not told to
  resume or close the card `goc` itself lists as active.
- **Stop:** the opt-in `pattern_generalization_check` was read from the
  checkout's config, not the one `goc` reads, so enabling it in the primary
  tree left it off in every linked worktree branched before the change.

The agreement test (`tests/test_project_root_from_subdirectory.py`,
`HookProjectDirWalkTest`) compared the hooks to the engine over layouts with no
worktree in them, so the missing redirect was outside what it checked.

## Evidence

`reproduce.py` builds a primary repo with `goc install --agents claude`,
uncomments the config template's own `worktree_deck: shared` line, commits,
adds a linked worktree, and from it creates and claims a card with `goc`. It
then runs both hooks with `cwd` = each tree. Before the fix:

```
card in primary deck=True; in linked checkout=False; goc --status active from linked lists it=True
session-start names the card: cwd=primary True; cwd=linked False
stop hook exit (2 = enabled, blocks): cwd=primary 2; cwd=linked 0

FAIL: from the linked worktree the hooks read its own checkout, not the shared deck goc uses.
```

After:

```
session-start names the card: cwd=primary True; cwd=linked True
stop hook exit (2 = enabled, blocks): cwd=primary 2; cwd=linked 2

OK: from the linked worktree both hooks follow the shared deck goc uses.
```

Both halves of the hypothesis held; the Stop-hook half, which the filing agent
had not re-run, reproduced as reported.

## What changed

- Both hooks carry the same new block ahead of `_find_project_dir`
  (`deck_session_start.py:275-402`, `pattern_generalization_check.py:93-220`):
  `_detect_worktree_common_root` and `_shared_worktree_deck_root` mirror the
  engine functions of the same names, and `_find_project_dir` runs the redirect
  before the walk. Its docstring now calls the whole resolution the mirror.
  The git probe also treats a hook-input `cwd` that is gone or not a directory
  as "not a worktree", where the engine only ever probes its own process cwd.
- The engine reads the opt-in with yaml_lite, which the hooks cannot import.
  `_config_shares_the_deck` reads the block layout the config template ships:
  the key one level under the top-level `workflow:`, comment lines skipped (so
  the template's commented-out line stays off), the bare or quoted word with at
  most a trailing comment. Where yaml_lite refuses the file, the engine leaves
  the redirect off; the reader does the same for a tab in the indentation and a
  repeated top-level or `workflow` key — the second-`workflow:`-block edit is
  the easy way to get this wrong while enabling the option.
- `goc/engine.py` `_resolve_deck_root`'s docstring says the hooks mirror the
  redirect and the walk both.
- `tests/test_project_root_from_subdirectory.py` `HookProjectDirWalkTest`
  gains three tests: the hooks agree with `engine._resolve_deck_root` from a
  linked worktree and a directory inside it with no opt-in, the env-var opt-in
  (spelled `Shared`, for the engine's case-insensitive compare) and the config
  opt-in; the config reader agrees with `engine._shared_worktree_deck_root` over
  19 config texts, including the shipped template before and after its line is
  uncommented; and both hook scripts, run as subprocesses from inside a
  shared-deck worktree, name a card `goc` claimed there and read the primary
  tree's Stop-hook opt-in. Against the pre-fix hooks the three tests fail
  (9 failed and 36 errored subtests). The config-reader and subprocess tests
  are the fifth DoD box: the reader is hand-derived logic the original DoD did
  not anticipate, and only a subprocess run shows each hook's `main()` acting
  on the resolved root.
- Mirrors re-synced: `.claude/hooks/`, `claude-plugin/` and `codex-plugin/`
  hook copies, and the engine copies in all three plugin payloads.

## Limits

- A flow-style `workflow: {worktree_deck: shared}` turns the engine's redirect
  on but not the hooks'. The template ships the block form, so the reader
  stops there; it is the residue the parity decision on
  [session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
  would remove.
- yaml_lite refuses other malformed files (a repeated key deeper in another
  block, an over-indented line). The engine then leaves the redirect off while
  the hooks may still read a well-formed `workflow` block.

## Related

- [openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution](../openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution/)
  (gate decision): the OpenClaw TypeScript port has the same gap and more; its
  fix waits on the reimplement-or-delegate decision. The Python hooks had no
  delegate option (they import nothing), so this card took the reimplement
  path; the config reader above is the scope a TypeScript port would carry.
- [session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting](../session-start-hook-reimplements-engine-waiting-and-frontmatter-logic-and-keeps-drifting/)
  (gate decision, meta-fix): this card advances it as one more hand-derived
  engine predicate that drifted, the first outside the waiting/frontmatter
  family and shared by both hooks.
