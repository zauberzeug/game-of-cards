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

## 2026-06-19 — promoted: defect verified, `unverified` tag dropped

Ran the falsification recipe end-to-end (`reproduce.py` lands in the card
dir). Result: the defect is **reachable** and confirmed.

- The card's own `worker: {where: feature/x}` input is rejected by
  `goc validate` with `mapping must have a 'who' key` — a missing-key error.
- Running `goc wait scratch-card --reason external` (a full-frontmatter
  re-emit verb) succeeds (exit 0) and rewrites the line to
  `worker: {who: "", where: feature/x}` — `_emit_worker` defaulted the
  missing `who` to `""`.
- A second `goc validate` now reports a *different* error:
  `'who' must be a non-empty, non-whitespace string`.

So the emitter does not just preserve a malformed worker; it invents an empty
`who` the author never wrote, while the verb claims success. Six verbs reach
this path (`wait`/`decide`/`advance`/`unadvance`/`quality-pass`/
`migrate-list-style`); `goc status active` and the `done` paths use
line-anchored `mutate_frontmatter_field` and are unaffected.

Dropped `unverified` from `tags` and checked the first DoD box. The card stays
`human_gate: decision`: the PROCESS item (refuse vs normalize) is a genuine
behavioral choice — refusing makes the listed verbs *crash* on a malformed
worker; normalizing must decide what to do with the orphaned `where`. The
2026-06-06 sibling note above argues the decision should settle both sites at
once by routing all worker emission through one guarded helper. Left for a
human to decide; the fix was NOT applied.
