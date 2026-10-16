## 2026-10-16T04:40:00Z — Filed

Filed by an audit-deck pass that a pull-card run started when the ready queue was
empty (every gate-free open card carries an active `waiting_on`). Found while
reading the deck-root resolution in `goc/engine.py`: `_detect_worktree_common_root`
compares the raw `git rev-parse` text, and git prints `--git-dir` as an absolute
path but `--git-common-dir` as a relative one from a subdirectory of the primary
checkout. `reproduce.py` shows the detector misfiring in the engine and both
Python hooks, plus three user-visible symptoms under the opt-in.

Dedup: no card names `_detect_worktree_common_root` or `--git-common-dir`'s output
form. The nearest cards are different defects. `deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in`
(done) bounds the walk when the opt-in is off. `python-hooks-ignore-git-worktree-shared-deck-resolution`
(done) gave the hooks a copy of the redirect, and this misfire came with that copy.
`openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution` (open) is
about the OpenClaw port having no worktree probe at all.

Gate none: the documented contract (the opt-in applies to linked worktrees only)
determines the answer, and comparing the resolved paths is the only change. It is a
fix-through candidate: one function, kept identical in three copies that a test
already pins together.
