## 2026-06-06 — related evidence: empty-`who` is reachable at a sibling site

A pull-card audit found and fixed a *distinct* site that emits the same
invalid empty-`who` worker:
[goc-status-active-stamps-empty-who-worker-when-git-user-name-unset](../goc-status-active-stamps-empty-who-worker-when-git-user-name-unset/)
(closed 2026-06-06). There `_auto_populate_worker` (engine.py:4290) hand-built
`worker: {who: "", where: <branch>}` on a fresh `goc status active` claim when
git `user.name` was unset — proven reachable via reproduce.py.

That fix was local (skip the stamp when `who` is empty) and does NOT touch
`_emit_worker`, so this card's hypothesis stands. But the two sites together
are the real signal: worker-value serialization is **duplicated** —
`_auto_populate_worker` builds the inline string by hand instead of delegating
to `_emit_worker` — and each copy can independently emit the invalid shape. The
generalized fix for this card should consider routing all worker emission
through a single guarded helper (refuse/normalize empty `who` in one place) so
the class cannot recur at a third site, rather than patching `_emit_worker` in
isolation. The "refuse vs normalize" decision this card already poses is the
right place to settle it for both sites at once.
