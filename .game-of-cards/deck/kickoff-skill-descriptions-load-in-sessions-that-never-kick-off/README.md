---
title: kickoff-skill-descriptions-load-in-sessions-that-never-kick-off
status: disproved
stage: null
contribution: low
created: "2026-07-07T04:31:05Z"
closed_at: "2026-07-11T00:54:26Z"
human_gate: none
advances: []
advanced_by: []
tags: [story, infra]
summary: |-
  DISPROVED: the feared four-description overhead does not exist on any
  payload. All four consumer surfaces (claude-plugin, codex-plugin,
  openclaw-plugin, per-agent vendored installs) already filter
  host-specific kickoff complements, so every session carries exactly
  two kickoff descriptions — generic `kickoff` (243 chars) plus the
  host's own complement (225–278 chars), ~470–520 chars total.
  Consolidation would save one ~250-char description per session at the
  cost of install/upgrade removal handling, sync/porter/parity churn —
  not worth it.
definition_of_done: |
  - [x] EMPIRICAL: per-host measurement recorded in log.md — which kickoff-family descriptions each payload (claude-plugin, codex-plugin, openclaw-plugin, pipx/vendored install) actually injects into a consumer session.
  - [x] PROCESS: verdict recorded — consolidate (host complements become reference files of the generic kickoff, mirrors/porter updated) or disprove (filtering already bounds the cost; card flips to disproved with the numbers). Verdict: disprove.
  - [x] MECHANICAL: if consolidating — install/upgrade paths, sync script, porter, and validate parity handle the removed skill dirs; full test suite and both --check guards green. N/A — verdict is disprove; no consolidation performed.
worker: {who: "claude[bot]", where: main}
---

# Kickoff skill descriptions load in sessions that never kick off

> ⚠ **Verdict: DISPROVED (2026-07-11).** Per-host filtering already
> caps the cost at two descriptions per session on every payload;
> consolidation does not pay for its churn.

## Hypothesis (as filed)

Kickoff-family skills run once per repo lifetime, yet a consumer that
finished setup months ago might still pay for up to four kickoff
descriptions (`kickoff`, `claude-kickoff`, `codex-kickoff`,
`openclaw-kickoff`; ~1.4 KB pre-trim) in every session's system prompt,
because skill hosts inject every installed skill's description. If so,
folding the host complements into the generic `kickoff` as on-demand
reference files would cut the standing cost to one description.

## Verdict (FALSE — what's actually shipped)

Every consumer surface already filters host-specific complements, so no
session ever sees more than **two** kickoff descriptions: generic
`kickoff` plus the one complement for its own host.

| Payload | Kickoff dirs shipped | Filter mechanism |
|---|---|---|
| `claude-plugin/skills/` | `kickoff`, `claude-kickoff` | `sync_plugin_assets.py` excludes names failing `skill_for_agent(name, "claude")` |
| `codex-plugin/skills/` | `kickoff`, `codex-kickoff` | same, for `"codex"` |
| `openclaw-plugin/skills/` | `kickoff`, `openclaw-kickoff` | porter `HOST_PREFIXES = ("claude-", "codex-")` skip list |
| pipx/vendored `goc install` | per agent tree: `kickoff` + that agent's complement | `skill_for_agent` in `goc/install.py` (`_iter_skill_assets` / `_sync_skill_tree`) |

A dual claude+codex vendored install writes `kickoff` +
`claude-kickoff` to `.claude/skills/` and `kickoff` + `codex-kickoff`
to `.codex/skills/` (this repo's own dogfood trees confirm it), and
each host session loads only its own tree — still two per session.

Measured description sizes (source templates): `kickoff` 243 chars,
`claude-kickoff` 225, `codex-kickoff` 273, `openclaw-kickoff` 278.
Worst-case standing cost per session: 243 + 278 = 521 chars (~130
tokens); all are already under the 300-char description cap.
Consolidating would recover only the ~225–278-char complement
description — against real churn: install/upgrade cleanup of removed
skill dirs on existing consumer repos, sync-script and porter updates,
parity-tripwire adjustments, and plugin-payload relayout.

## Source of error

The card was filed from the source-of-truth view
(`goc/templates/skills/` contains all four dirs) without checking that
every downstream consumer filters that tree per host. The filer noted
the OpenClaw porter's filtering but treated the claude/codex payloads
and the `goc install` path as unverified — they in fact use the same
`skill_for_agent` predicate.

**Lesson:** `templates/skills/` is a superset; per-host shipping is
decided by `skill_for_agent`, which every consumer (install, sync
script, porter) already applies. Measure the shipped payloads, not the
template tree.
