## 2026-05-29T18:59:23Z: decision deliberation archived

Archived from the README's `## Decision required` section by `goc decide` before it was replaced with the resolved `## Decision` block — README is the dashboard, log.md is the journal. This preserves the options and recommendation that produced the decision below.

The cluster of unguarded mutation verbs (`_cmd_quality_pass`, `_cmd_wait`, `_cmd_attest`) suggests two distinct fix shapes worth picking between:

- **(a) Verb-level filter at quality-pass entry**: `_cmd_quality_pass` always filters terminal-status cards out of the *LLM sample* (the variable `sample` at engine.py:4816), regardless of `--status` value. Layer-1 antipattern/missing-summary scan continues to include terminal cards (read-only, useful for hygiene reporting). Layer-2 LLM rewrite path never sees them. Simple, defense at the boundary.
- **(b) Verb-level error**: `_cmd_quality_pass` rejects `--llm` combined with `--status all|done|disproved|superseded` with an explicit error message. Matches the `_cmd_decide` shape — fail loudly. Slightly less ergonomic if the user wanted Layer-1 hygiene reporting on terminal cards.
- **(c) Helper-level guards**: `_apply_summary_rewrite` and `_apply_dod_rewrite` refuse with a `ValueError` when the card is terminal. Defense-in-depth: protects any future caller, not just quality-pass. Matches the post-fix `_cmd_decide` shape but applied to the helpers.

Recommendation: **(a) + (c) combined** — filter at the verb so the common path silently does the right thing, and guard the helpers so any new caller (a future `goc rewrite-summary` verb, an internal tool) inherits the protection.


## 2026-10-22T05:17:58Z: decision recorded

Decided via parent terminal-status-guard-missing-across-mutation-verbs: (a) + (c) combined — filter terminal cards out of the Layer-2 LLM sample regardless of --status, and guard _apply_summary_rewrite / _apply_dod_rewrite — The maintainer approved the parent's recommended bundle in a human session on 2026-10-22, which resolves exactly this card's question; implement through the parent's shared _refuse_terminal_mutation helper, whose message is written fresh because _cmd_decide no longer refuses terminal cards. Gate decision → none.
