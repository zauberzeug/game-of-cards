---
title: openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry
summary: "The OpenClaw plugin's loadable artifact is the committed esbuild output `openclaw-plugin/dist/index.js`, but nothing in the repo checks it against `openclaw-plugin/index.ts`. Every other generated tree has a byte-for-byte tripwire (`sync_plugin_assets.py --check`, `port_skills_to_openclaw.py --check` + a regression test); dist/ has none, and the pre-commit sync hook is scoped `files: ^goc/` so an index.ts-only edit fires no hook at all. Verified: a TypeScript edit with a stale dist passes all 771 tests, both --check scripts, and goc validate."
status: open
stage: null
contribution: high
created: "2026-07-26T08:04:27Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry

(write the design doc here)
