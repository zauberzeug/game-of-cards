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
