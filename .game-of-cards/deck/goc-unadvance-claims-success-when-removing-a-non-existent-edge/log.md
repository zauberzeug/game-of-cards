## 2026-05-29T19:29:58Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible failure modes; the engine has analogues for all three and the
project hasn't settled on a convention for "non-mutating verb call":

1. **`exit 2 + ERROR on stderr`** — matches `_cmd_advance`'s self-edge and
   cycle handling (engine.py:6573, 4393). Strictest: a no-op verb call is a
   user error, surface it.
2. **`exit 0 + WARNING on stderr + no success message`** — least disruptive
   to scripts that call `unadvance` defensively; still distinguishable from
   a real removal. Matches the "advisory" tone of the `STALE_BLOCKED` /
   `ORPHAN_BLOCKED` validators.
3. **`exit 0 + "no edge to remove" success line`** — silent acceptance of
   the idempotent shape. Matches `_remove_from_list_field`'s own no-op
   return (engine.py:6324). Least intrusive but loses information.

Whichever shape the implementer picks should also cover the analogous
`goc wait --clear` on a card without a wait (currently unverified — check
`_cmd_wait` for the same pattern when implementing) so the convention
applies consistently across the verb set.


## 2026-10-22T05:20:22Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR on stderr — removing a non-existent edge is refused, symmetric with the advance sibling — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.
