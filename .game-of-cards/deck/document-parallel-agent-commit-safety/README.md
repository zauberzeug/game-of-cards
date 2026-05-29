---
title: document-parallel-agent-commit-safety
summary: "The parallel-agent commit-safety rule from `../phasor-agents/CLAUDE.md` should be captured in this repo's shared root guidance and in the `finish-card` commit handoff. Document the shared-index staging discipline: wait for a free index, stage explicit paths, verify staged files, commit with pathspecs, avoid stash/destructive cleanup, and prefer worktree commit prep for risky shared-main commits."
status: done
stage: null
contribution: medium
created: "2026-05-18T03:52:42Z"
closed_at: "2026-05-18T03:54:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [x] `AGENTS.md` documents the parallel-agent shared-index commit-safety discipline for local `main` work.
  - [x] `goc/templates/skills/finish-card/SKILL.md` Step 8 includes the same commit-handoff rule in actionable form.
  - [x] Dogfood/plugin `finish-card` skill copies are in sync with the template.
  - [x] `uv run goc validate --quiet` passes.
worker: {who: Rodja Trappe, where: main}
---

# Document parallel-agent commit safety

## Summary

`../phasor-agents/CLAUDE.md` has a useful "stage" trick for multiple
agents working on local `main`: treat Git's index as shared state.
Before staging, check whether another agent already has staged files;
stage only explicit paths; verify the staged set; and commit with an
explicit pathspec so unrelated staged files cannot accidentally be
bundled.

## Location

- `AGENTS.md`
- `goc/templates/skills/finish-card/SKILL.md`
- generated mirrors under `.claude/skills/` and `claude-plugin/skills/`

## Work

Add a concise root-guidance rule and a `finish-card` Step 8 handoff rule
covering:

- wait/back off if `git diff --cached --name-only` shows files owned by
  another agent;
- use `git add <explicit-file>...`, never broad staging;
- verify with `git diff --cached --stat`;
- commit with `git commit -- <explicit-file>...`;
- avoid `git stash`, destructive restore/reset/clean, and unrelated
  index cleanup;
- prefer a temporary worktree for high-risk shared-main commit prep.
