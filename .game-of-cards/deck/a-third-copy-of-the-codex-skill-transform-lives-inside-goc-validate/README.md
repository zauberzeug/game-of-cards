---
title: a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate
summary: "The Codex SKILL.md normalization has three independent implementations, not the two the open consolidation card enumerates: `goc/install.py:1367` (the writer), `scripts/sync_plugin_assets.py:350` (the mirror generator), and a third nested inside `validate_plugin_mirror_parity` at `goc/engine.py:1780`. The third is also the one that missed two hardening fixes the other copies carry — it compares mirror siblings with `read_text()` where the sync script deliberately uses `read_bytes()` so newline skew stays CI-detectable, and it skips `dst_item.is_dir()` where the sync script flags empty orphan directories. The weaker of the two guards is the one that ships to consumers. Parked unverified: citations read and confirmed, no reproduce.py built this round."
status: open
stage: null
contribution: medium
created: "2026-09-21T01:23:36Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [infra, api-contract, meta-fix, unverified]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# a-third-copy-of-the-codex-skill-transform-lives-inside-goc-validate

(write the design doc here)
