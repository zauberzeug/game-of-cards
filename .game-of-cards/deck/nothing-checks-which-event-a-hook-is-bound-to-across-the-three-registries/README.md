---
title: nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries
summary: "AGENTS.md says the hook event mapping stays hand-written in three registries because a command is not derivable from a script name, and that `goc validate` covers all three. It covers only the script *set*: `_plugin_registered_hook_scripts` (engine.py:1520-1543) walks `data['hooks'].items()` but lets `event` reach error strings only, and the parity check at engine.py:1594-1604 compares name sets in both directions. So a script bound to the wrong event in one payload — the session primer on Stop, the prompt router on SessionStart — passes every tripwire and fails only at runtime, silently. Parked unverified: citations read and confirmed, no reproduce.py built this round."
status: open
stage: null
contribution: medium
created: "2026-09-21T01:23:36Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract, unverified]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# nothing-checks-which-event-a-hook-is-bound-to-across-the-three-registries

(write the design doc here)
