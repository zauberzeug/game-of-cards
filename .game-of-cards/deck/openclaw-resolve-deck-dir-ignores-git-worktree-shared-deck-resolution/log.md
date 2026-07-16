## 2026-07-16T01:13:44Z — Drift widened: engine gained a bounded ancestor walk

Engine `_resolve_deck_root` now also resolves the nearest deck-owning
ancestor (commit 3e17e3b3) with a working-tree boundary rule (commit
30355095, closing
deck-root-ancestor-walk-escapes-nested-worktree-into-primary-deck-without-opt-in).
`resolveDeckDir` in openclaw-plugin/index.ts mirrors none of it, so the
omission count in this card's README moved from two behaviors to three.
Strengthens the delegate-to-engine option in the pending decision.
