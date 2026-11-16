## 2026-11-16T01:30:00Z — Parked as unverified by audit-deck

A hunter candidate: the audit's general-purpose subagent reproduced it on
scratch decks. The auditing agent read `is_placeholder_scaffold`
(`goc/engine.py:2992-3005`), the refusal text (`:6901-6902`) and the
reference's Draft contract (`:62-63`), and reproduced both half-authored
cases by hand. The output is in the README. Parked without a
`reproduce.py` under the audit's park-or-disprove rule.

- **Dedup**: `is_placeholder_scaffold`, `SCAFFOLD_DOD_PLACEHOLDER`,
  `replace with real criteria`, `pure placeholder` and `half-authored`
  turned up no decision that half-authored drafts may be published.
  [placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/)
  (done) introduced the check and got a post-close amendment pointing here.
