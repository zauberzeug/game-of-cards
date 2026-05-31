## 2026-05-31T08:58:10Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Pick the scope before implementing (see DoD PROCESS item):

1. **Audit-only** — enumerate the invariants and the producing/repairing
   verb for each; file a per-gap card where no repair verb exists. Cheapest;
   defers the build.
2. **General `goc repair`** — extend `repair-edges` into a `goc repair
   [--apply]` that fixes every mechanically-repairable violation and lists
   the judgment-needing ones. Most user value; largest build.
3. **Hybrid** — audit now, build `goc repair` incrementally as gaps are
   confirmed.


## 2026-05-31T09:32:46Z: decision recorded

Audit-only: land the validator-invariant × repair-verb enumeration as a durable reference in this card; file targeted per-gap cards only where a repair verb is genuinely warranted (the mechanical closed_at gap), and point at the already-open cards for the rest — The audit shows most validator gaps need human judgment to repair (which successor / which tag / what summary), so a general goc repair would only mechanically auto-fix a minority while adding a large build; the enumeration plus a couple of targeted follow-ups is the higher-ROI, honest scope. Gate decision → none.
