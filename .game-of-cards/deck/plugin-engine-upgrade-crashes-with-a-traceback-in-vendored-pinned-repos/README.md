---
title: plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos
summary: "In any repo pinned skills_source: vendored (what the documented \"goc install --local-skills\" writes), running \"goc upgrade\" from a plugin-bundled engine dies with an unhandled FileNotFoundError on templates/skills — the directory all three plugin payloads deliberately omit. The plugin-context refusal guards only the explicit --keep-local-skills flag, but upgrade() re-derives the same vendored mode from config.yaml with no such check, and --dry-run crashes identically so the user cannot even preview."
status: open
stage: null
contribution: high
created: "2026-09-10T04:49:51Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos

(write the design doc here)
