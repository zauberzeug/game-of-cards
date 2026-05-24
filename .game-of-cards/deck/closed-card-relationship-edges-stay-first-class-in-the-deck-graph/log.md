## 2026-05-24T04:05:00Z: decision recorded

A1 (typed bidirectional superseded_by/supersedes field) + B1+B2 (compute_values warns AND goc validate errors on dangling advances targets) — Typed successor link matches ADR/issue-tracker convention and makes supersession machine-navigable; surfacing dangling edges both at compute time (warn) and in validate (error) makes edge rot impossible to miss, not merely visible.. Gate decision → none.

### Deliberation archived (options the decision resolved)

Archived here because `goc decide` replaces the README's `## Decision
required` section with the one-line `## Decision` block and does not yet
journal the deliberation itself (see open card
goc-decide-loses-deliberation-history-by-not-archiving-replaced-section).

**A. Successor-pointer modelling** — chosen: **A1**.

- A1 — new typed bidirectional field (`superseded_by` / `supersedes`),
  auto-symmetric like `advances`. Cleanest semantics, matches
  ADR/issue-tracker convention. Cost: schema + skill + emitter + validator
  + a new invariant. **(chosen)**
- A2 — reuse the `advances` graph, distinguished by status. No new field,
  but overloads value-flow semantics with succession and risks the GRPW
  value walk composing priority through supersession edges. (rejected)
- A3 — prose-only status quo. Zero build cost; rejected-by-default given
  the prior art. (rejected)

**B. `compute_values` behaviour on a dangling `advances` target** — chosen:
**B1 + B2** (both).

- B1 — keep walking but emit a warning (and surface in `goc validate`).
  **(chosen)**
- B2 — `goc validate` errors on any dangling `advances` target, forcing
  repair (consistent with half-edge treatment). **(chosen)**
- B3 — silent skip (status quo). This is the bug. (rejected)

Original card recommendation was A1 + B2; the decision additionally adopts
B1, so a dangling target both warns at compute time AND fails validation —
rot is impossible to miss at either entry point.
