## 2026-11-16T01:30:00Z — Parked as unverified by audit-deck

A hunter candidate: the audit's general-purpose subagent, briefed on the
scheduler core, reproduced it on scratch decks with both `goc publish` and
`goc status <title> active`. The auditing agent read the cited lines
(`goc/engine.py:6872`, `:6925`, `:7097-7098`, `:7116`) and reproduced the
publish path by hand. The output is in the README. Parked without a
`reproduce.py` under the audit's park-or-disprove rule.

- **Dedup**: `commit_targets`, `_git_auto_commit([card_dir]`, `half-edge`
  with publish or claim, and `explicit-pathspec` are all covered.
  [goc-new-with-advances-leaves-parent-card-mutation-uncommitted](../goc-new-with-advances-leaves-parent-card-mutation-uncommitted/)
  (done) assumed the half-edge depends on the agent's own staging. That
  closed card got a post-close amendment pointing here.
