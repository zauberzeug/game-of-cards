## 2026-05-29T19:53:19Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

Two credible failure-mode shapes; pick one:

1. **`exit 2 + ERROR before any mutation`** (strict). Mirrors the
   existing terminal-status guard at `engine.py:4909` and the
   already-`none` gate guard at `engine.py:6866`. The natural choice
   because the resulting body and log entry are not human-readable —
   there is no "lenient success" interpretation that produces a useful
   audit trail. Breaks no tooling that wasn't already producing
   corrupt output.
2. **`exit 0 + WARNING on stderr + still record`** (lenient). Keeps
   the option open for tooling that wants to record a "decided but
   undocumented" state for later annotation. Less appealing — the
   README block and log entry are equally corrupt either way, and a
   "WARNING then succeed" path is the harder-to-discover variant of
   the same broken contract.

Strict (option 1) is the natural sibling of the existing guards in
the same function. Adopt strict unless a concrete tooling use case
appears for the lenient form.


## 2026-10-22T05:20:22Z: decision recorded

Decided via parent mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success: option 1, exit 2 + ERROR before any mutation for an empty --decision or --because — The maintainer decided the parent's shared validation-failure shape (1. Strict-refuse) in a human session on 2026-10-22, which answers exactly this card's question. Gate decision → none.
