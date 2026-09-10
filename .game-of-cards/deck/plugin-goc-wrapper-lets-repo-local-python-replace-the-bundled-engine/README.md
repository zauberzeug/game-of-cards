---
title: plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine
summary: "The plugin bin/goc wrappers invoke \"python3 -m goc.cli\", and -m puts the invocation cwd at sys.path[0] — ahead of the plugin root supplied via PYTHONPATH. Any consumer repo containing a top-level goc/ package silently takes over the goc command in that session, and a repo-root module shadowing a stdlib name the engine imports hard-crashes the wrapper instead. The plugin advertises a bundled engine; what actually runs is decided by repo content."
status: open
stage: null
contribution: high
created: "2026-09-10T04:50:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine

(write the design doc here)
