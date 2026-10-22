## 2026-10-16T04:36:58Z — Filed

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

## 2026-10-16T04:42:36Z — Closure

- **What changed**: `goc/engine.py:65-70`, `goc/templates/hooks/deck_session_start.py:306-311`,
  `goc/templates/hooks/pattern_generalization_check.py:121-126`. `_detect_worktree_common_root`
  resolves both `git rev-parse` outputs against the directory git ran in and compares the
  paths, so a primary-checkout subdirectory no longer reads as a linked worktree. The engine
  and both hook copies changed in lockstep, and the docstrings say why.
  `tests/test_project_root_from_subdirectory.py` gains `PrimaryCheckoutIsNotALinkedWorktreeTest`
  with 3 tests. Plugin and dogfood mirrors were re-synced.
- **Verification**: reproduce.py went from exit 1 (6 checks DEFECT) to exit 0 (all ok). Run
  against the pre-fix tree in a detached worktree at `1c39ce04`, the new tests fail 5 subtests
  (the `src/pkg` case for each of the three readers, plus both symptom tests). The
  linked-worktree subtests pass before and after. `sync_plugin_assets.py --check` and
  `port_skills_to_openclaw.py --check` are green, and `goc validate` exits 0.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1322 passed / 0 failed / 0 xfailed (`tests/test_project_root_from_subdirectory.py` 13/13)
- **Bundled with**: none

## Closure verification (2026-10-16T04:42:38Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 5/5 ticked
- [x] log-md-closure-entry — '## 2026-10-16 — Closure' present
