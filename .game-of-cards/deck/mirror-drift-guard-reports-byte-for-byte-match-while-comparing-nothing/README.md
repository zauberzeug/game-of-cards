---
title: mirror-drift-guard-reports-byte-for-byte-match-while-comparing-nothing
summary: "scripts/sync_plugin_assets.py's __pycache__/.pyc exclusion substring-matches the ABSOLUTE path instead of the path's parts and suffix, so on any checkout whose directory name contains one of those fragments every source and destination item is skipped. --check then prints \"OK — byte-for-byte\" having compared nothing, and the pre-commit auto-sync stages nothing. The three sibling implementations of the identical exclusion all scope it correctly to .parts/.suffix."
status: open
stage: null
contribution: medium
created: "2026-09-10T04:51:50Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# mirror-drift-guard-reports-byte-for-byte-match-while-comparing-nothing

(write the design doc here)
