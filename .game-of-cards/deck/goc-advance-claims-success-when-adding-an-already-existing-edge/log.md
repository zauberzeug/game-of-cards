## 2026-05-29T19:42:01Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Three credible options for the failure mode; pick one and apply to BOTH
add and remove directions consistently:

1. **`exit 2 + ERROR`** — strict, mirrors `cannot advance a card with
   itself`. Maximally clear, but breaks any script that retries
   `goc advance` defensively (the second call is currently a quiet
   success; making it a hard failure changes existing behavior).
2. **`exit 0 + WARNING on stderr`** — backward-compatible: the success
   line still fires on stdout, but a `WARNING: edge already exists`
   joins it on stderr. Scripts keep working; humans get an honest
   signal.
3. **`exit 0 + no-op success message`** — replace the misleading
   `advance: ...` line with a distinct `noop: b.advanced_by already
   contains a; nothing to do`. Same exit code as today, distinct
   stdout, easy to grep.

The right choice depends on the resolution of the sibling card; this
card's fix should land second and adopt whichever shape that card picked
so the two verbs stay symmetric.


## 2026-10-22T05:20:21Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR — adding an already-existing edge is refused and mutates nothing, symmetric with the unadvance sibling — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.
