---
title: goc-verbs-emit-frontmatter-their-own-validator-rejects
summary: "Aggregation epic for a family of first-party `goc` verbs that exit 0 with a success line after writing frontmatter `goc validate` then rejects. Four independently-filed instances span `new`, `status active`, `publish`, `done` and the full-frontmatter re-emit verbs — `goc status active` alone self-corrupted twice and took two separate point fixes. The root cause is structural: each writer re-derives its own notion of a legal value, so nothing ties the writers' accept-set to `validate_card`'s, and every tightening of the validator silently opens a new gap in a writer. Needs a mechanism decision (shared predicates, a validate-the-result assertion, or schema-driven per-field validators) before another point fix."
status: open
stage: null
contribution: high
created: "2026-08-07T05:35:15Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - worker-mapping-with-only-a-branch-emits-invalid-empty-who
  - draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck
  - blank-worker-overrides-write-cards-that-goc-validate-rejects
  - goc-status-active-stamps-empty-who-worker-when-git-user-name-unset
tags: [epic, meta-fix, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# goc-verbs-emit-frontmatter-their-own-validator-rejects

(write the design doc here)
