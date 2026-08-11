---
title: zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface
summary: "The zero-match queue line's hidden-draft count replays only filter_cards, not the --closed-since and --waiting conjuncts _cmd_default applies after it, so `goc --waiting --status open` and `goc --closed-since 1h --status done` report drafts as hidden from queries those drafts would not match even once published. live_impeded carries a third inlined draft conjunct that the predecessor card's include_drafts thread never reached, so under --waiting the count cannot be evaluated counterfactually at all. The clause exists to separate a drained deck from a deck of scaffolds; miscounted, it sends the reader to `goc publish` for nothing."
status: open
stage: null
contribution: medium
created: "2026-08-11T05:24:17Z"
closed_at: null
human_gate: none
advances:
  - query-flag-validation-is-opt-in-per-flag-and-new-flags-keep-missing-it
advanced_by: []
tags: [bug, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# zero-match-line-claims-hidden-drafts-that-publishing-would-not-surface

(write the design doc here)
