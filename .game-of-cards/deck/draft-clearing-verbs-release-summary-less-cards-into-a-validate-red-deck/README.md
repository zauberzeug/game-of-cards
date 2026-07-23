---
title: draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck
summary: "goc publish, goc status active, and goc done clear the draft flag without checking the summary field, but validate now errors on any non-draft card missing a summary. A first-party verb sequence (goc new without --summary, author DoD/body, publish or claim) exits 0 while leaving the deck failing its own validator, which blocks the next commit in repos using the shipped pre-commit hook."
status: open
stage: null
contribution: medium
created: "2026-07-23T13:24:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# draft-clearing-verbs-release-summary-less-cards-into-a-validate-red-deck

(write the design doc here)
