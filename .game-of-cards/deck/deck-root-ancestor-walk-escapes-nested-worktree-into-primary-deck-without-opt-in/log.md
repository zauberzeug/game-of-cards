## 2026-07-16T01:11:29Z — Closure

- **What changed**: goc/engine.py:99-113 (`_resolve_deck_root`) — the fallback ancestor walk now tracks when it has passed the current tree's own root (first candidate carrying a `.git` entry) and breaks on any later `.git`-carrying candidate, so a foreign working tree's deck is never inherited without the worktree_deck=shared opt-in. Docstring updated; mirrors regenerated.
- **Re-scope during implementation**: the filed Fix proposed stopping at the *first* `.git` boundary, but commit 3e17e3b3's own test `test_new_from_nested_repo_uses_ancestor_deck` pins deliberate plain-workspace inheritance (deck-less nested repo → enclosing non-git workspace deck). The rule was narrowed to "stop before entering a *different* working tree", which preserves both pinned tests; README Fix section rewritten in place.
- **Verification**: reproduce.py exit 0 (`goc new` from a deck-less nested worktree now exits 2, no cross-tree write); new tests `test_new_from_nested_worktree_refuses_without_shared_opt_in` and `test_new_from_repo_nested_in_deck_owning_repo_refuses` pass.
- **Audit**: PASS — no rubric configured; aligns with the opt-in contract pinned by spike-worktree-auto-resolves-deck-from-main-repo ("Behavior is opt-in via config/env — some users may want a per-worktree deck").
- **Project impact**: n/a
- **Tests**: 730 passed / 0 failed (full suite; the lone pre-sync mirror-parity failure cleared after scripts/sync_plugin_assets.py)

## Closure verification (2026-07-16T01:11:37Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-07-16 — Closure' present
