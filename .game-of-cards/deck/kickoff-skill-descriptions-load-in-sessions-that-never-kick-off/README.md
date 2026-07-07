---
title: kickoff-skill-descriptions-load-in-sessions-that-never-kick-off
status: open
stage: null
contribution: low
created: "2026-07-07T04:31:05Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
summary: |-
  Four kickoff-family skills (kickoff, claude-kickoff, codex-kickoff,
  openclaw-kickoff) are one-time-setup flows, yet their catalog
  descriptions sit in every consumer session's system prompt forever.
  Investigate how much each host payload actually ships (OpenClaw already
  filters host-specific complements), then fold host complements into the
  generic kickoff as on-demand reference files — or disprove the win if
  per-host filtering already caps the cost at one description per host.
definition_of_done: |
  - [ ] EMPIRICAL: per-host measurement recorded in log.md — which kickoff-family descriptions each payload (claude-plugin, codex-plugin, openclaw-plugin, pipx/vendored install) actually injects into a consumer session.
  - [ ] PROCESS: verdict recorded — consolidate (host complements become reference files of the generic kickoff, mirrors/porter updated) or disprove (filtering already bounds the cost; card flips to disproved with the numbers).
  - [ ] MECHANICAL: if consolidating — install/upgrade paths, sync script, porter, and validate parity handle the removed skill dirs; full test suite and both --check guards green.
---

# Kickoff skill descriptions load in sessions that never kick off

## Location

`goc/templates/skills/{kickoff,claude-kickoff,codex-kickoff,openclaw-kickoff}/SKILL.md`
descriptions; payload filtering in `scripts/sync_plugin_assets.py` and
`scripts/port_skills_to_openclaw.py` (the porter already skips
`claude-kickoff` / `codex-kickoff` as "host-specific complements").

## What's broken

Kickoff-family skills run once per repo lifetime, but skill hosts inject
every installed skill's description into every session's system prompt.
A consumer that finished setup months ago still pays for up to four
kickoff descriptions (~1.4 KB pre-trim; less since the 300-char cap) on
every prompt.

## Open question (why this needs measurement first)

The OpenClaw porter already excludes the claude/codex complements, so the
OpenClaw payload carries at most `kickoff` + `openclaw-kickoff`. If the
claude/codex payloads filter symmetrically, the realistic per-session
overhead is two descriptions, not four — and consolidation may not pay
for its churn (install/upgrade cleanup of removed skill dirs, parity
tripwires, plugin-payload layout). Measure per payload first; only then
decide consolidate vs disprove.

## Fix (if the measurement supports it)

Fold `claude-kickoff` / `codex-kickoff` / `openclaw-kickoff` into the
generic `kickoff` skill as host-specific reference files (same
progressive-disclosure pattern as
[`plugin-skills-consume-a-third-of-downstream-session-usage`](../plugin-skills-consume-a-third-of-downstream-session-usage/)):
one catalog entry, host detail loaded on demand during the one session
that actually kicks off.
