## 2026-10-14 — Instance: the deck-root resolution

`python-hooks-ignore-git-worktree-shared-deck-resolution` (advances this card)
is the first instance linked here outside the waiting/frontmatter predicates:
the hooks' `_find_project_dir` mirrored the engine's walk but not the
shared-deck worktree redirect before it, so from a linked worktree both hooks
read the checkout's own deck and config. The same resolution drifted once
before, when the hooks did not walk at all
(`goc-finds-the-deck-from-a-subdirectory-but-attests-validates-and-installs-there`,
closed). The fix mirrors the redirect, which brings a hand-rolled
reader of `workflow.worktree_deck` into both hooks. The reader is pinned with
the engine as its oracle:
`HookProjectDirWalkTest.test_hook_config_reading_agrees_with_the_engine`
compares it with `engine._shared_worktree_deck_root` over 19 hand-picked config
texts. That is the shape of option 1 below, over a chosen matrix rather than a
generated one, for one predicate. Known residue: a flow-style
`workflow: {...}` turns the engine's redirect on and not the hooks'.
