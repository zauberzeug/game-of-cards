---
title: board-active-card-worker-label-not-truncated
summary: "Keep board card titles visible when worker labels are appended to kanban cells."
status: done
stage: null
contribution: medium
created: "2026-05-18T04:41:30Z"
closed_at: 2026-05-18T04:43:11Z
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] Board cells render the full card title before the contribution marker even when a worker suffix is present
  - [x] Regression coverage reproduces an active `active-card` with worker `Rodja Tr`
  - [x] Existing active-card board/open-queue smoke coverage passes
worker: {who: Codex, where: work}
---

# Board active-card worker label not truncated

## Problem

The board renderer used a fixed 20-character column width and appended worker
labels inside that fixed budget. When an active card such as `active-card` had a
worker suffix like `[m] @Rodja Tr`, the title was shortened to `active`, so the
board view no longer displayed the actual card title that tests and users rely
on for coordination.

## Fix shape

Render each board cell once from the full title, contribution marker, and worker
suffix, then size each column to the widest rendered cell in that status column.
This keeps the board tabular while avoiding hidden title truncation in the
coordination view.
