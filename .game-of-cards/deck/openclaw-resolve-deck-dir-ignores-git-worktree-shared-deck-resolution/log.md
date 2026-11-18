## 2026-07-16T01:13:44Z — Drift widened: engine gained a bounded ancestor walk

Engine `_resolve_deck_root` now also resolves the nearest deck-owning
ancestor (commit 3e17e3b3) with a working-tree boundary rule (commit
30355095, closing
deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in).
`resolveDeckDir` in openclaw-plugin/index.ts mirrors none of it, so the
omission count in this card's README moved from two behaviors to three.
Strengthens the delegate-to-engine option in the pending decision.

## 2026-09-14 — refine-deck: defunct range cite corrected by hand

The Location block cited the engine's two-stage deck resolution at
`goc/engine.py:42-120`, with sub-ranges 42-94 and 97-120. Both endpoints
anchored on blank lines, so the citation recipe's text-equality check verdicted
the range `current` while the block moved. A line-level diff against the anchor
commit (`5997c92d`) maps the endpoints to 43 and 144.

Rewritten to the symbols' true HEAD boundaries rather than the drifted bracket:
outer `goc/engine.py:44-143` (`def _detect_worktree_common_root` through
`return canonical`), `_detect_worktree_common_root` / `_resolve_deck_root` at
44-118, `_resolve_deck_dir` at 121-143. The recipe gap is filed as
[citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank](../citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank/).

## 2026-10-14 — Python sibling fixed

`python-hooks-ignore-git-worktree-shared-deck-resolution` gave both Python
hooks the shared-deck redirect, mirrored from the engine because the hooks
cannot import it, with an engine-derived agreement test over a linked worktree
and 19 config shapes. Behavior 1 above is now an OpenClaw-only gap; the README
names the Python block as the reference for Option A. The decision itself is
untouched.

## 2026-10-16 — Reference block corrected

`shared-deck-mode-treats-primary-checkout-subdirectories-as-linked-worktrees` fixed
`_detect_worktree_common_root` in the engine and in the Python hook block that Option A
names as the code to port. git prints `--git-dir` absolute and `--git-common-dir`
relative from a subdirectory of the primary checkout, and the old raw-string
comparison read that as a linked worktree. A TypeScript port must compare the two as
resolved paths, the way the Python block now does. The decision itself is untouched.

## 2026-11-18 — Reference block corrected again

`shared-worktree-deck-finds-no-deck-when-the-repository-is-a-bare-clone` changed
`_detect_worktree_common_root` in the engine and in all three Python hook blocks.
The parent of git's common directory now counts as the primary working tree only
when that directory is a non-bare `.git`. `core.bare` is read with
`git config --file <common>/config`. A bare clone (`repo.git`, `.bare`, a bare
`.git`) and a git directory kept apart from its checkout return None, so shared
mode stays off there and the walk finds the worktree's own deck. A TypeScript port
under Option A must carry the same check, or it reintroduces the bare-clone defect.
The engine-only `WARNING` that names the ignored request is the CLI's concern. A
port that delegates to the engine (Option B) gets both for free. The decision
itself is untouched.
