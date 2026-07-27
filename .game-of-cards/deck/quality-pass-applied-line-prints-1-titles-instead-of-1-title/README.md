---
title: quality-pass-applied-line-prints-1-titles-instead-of-1-title
summary: "The quality-pass --llm apply summary at goc/engine.py:4255 hardcodes three plural nouns, so applying a single rewrite prints 'Applied: 1 titles, 0 summaries, 0 DoD items'. It is the one count banner the closed cards sweep left behind: the sweep's helper (_cards_noun) is card-specific and its CI guard only regexes cards?, so this line is neither fixed nor protected."
status: open
stage: null
contribution: low
created: "2026-07-27T01:30:21Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# quality-pass-applied-line-prints-1-titles-instead-of-1-title

(write the design doc here)
