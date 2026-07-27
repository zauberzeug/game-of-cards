---
title: static-source-guards-never-prove-they-can-catch-an-offender
summary: "Four static source-scanning guards in tests/ assert that goc/ or the doc tree contains no offending shape, but none of them is ever exercised against source that DOES offend — so a scanner whose pattern silently stops matching keeps the build green and reads as 'convention enforced'. This is the failure that cost two cards on the count-banner sweep: the guard inherited the sweep's own discovery regex and certified exactly the subset the sweep could already see. Two guards in the same suite already do it right, so the technique needs no invention — only a scope decision on how to apply it."
status: open
stage: null
contribution: medium
created: "2026-07-27T01:54:03Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [test, meta-fix]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# static-source-guards-never-prove-they-can-catch-an-offender

(write the design doc here)
