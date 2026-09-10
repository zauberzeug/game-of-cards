---
title: hook-catalogue-cites-an-audit-skill-section-that-never-existed
summary: "The deck README's Workflow-hook stubs table routes hooks/audit-deck.md authors to a \"Phase 0 priming reads\" section, but the audit-deck skill has no Phase 0 — its phases start at 1 and the hook is injected under \"## Context\"; git log -S shows the string never appeared in any shipped skill, so the row has been wrong since the catalogue was written on 2026-05-04 and has since been copied into five files. The table calls itself \"the authority\" and is backed by a regression test, but tests/test_readme_hook_catalogue_parity.py pins only the first column (the hook-stub set) — the \"Loaded by\" and \"Workflow point\" columns are unguarded prose."
status: open
stage: null
contribution: medium
created: "2026-09-10T04:36:58Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, test, meta-fix]
draft: true
definition_of_done: |
  - [ ] (replace with real criteria)
---

# hook-catalogue-cites-an-audit-skill-section-that-never-existed

(write the design doc here)
