---
title: query-views-each-decide-by-hand-which-filters-apply-and-keep-drifting
summary: "One goc query renders several views (the table or JSON, the board, the ACTIVE banner, the --ready leverage line and the zero-match line), and each decides by hand which of the query's filters it honors. That choice has drifted six times, each found as its own card; five are fixed, and --board still ignores every scope filter except --worker, so goc --board --tag documentation renders the whole deck. Make the query's scope one shared object every view reads, declare each deliberate exception, and guard it so a new view or a new filter cannot skip it."
status: open
stage: null
contribution: medium
created: "2026-10-08T05:20:41Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - active-card-banner-ignores-worker-filter
  - active-card-banner-tiebreak-undercounts-downstream-flow-under-worker-filter
  - board-worker-filter-hides-active-cards-by-applying-open-only-default
  - zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface
  - ready-leverage-line-compares-a-worker-scoped-pick-against-every-workers-gated-cards
  - board-view-silently-ignores-filters-other-than-status-and-worker
tags: [bug, meta-fix, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# query-views-each-decide-by-hand-which-filters-apply-and-keep-drifting

(write the design doc here)
