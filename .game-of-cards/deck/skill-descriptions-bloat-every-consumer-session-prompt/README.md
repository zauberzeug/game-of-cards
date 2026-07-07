---
title: skill-descriptions-bloat-every-consumer-session-prompt
status: active
stage: null
contribution: medium
created: "2026-07-04T13:47:46Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
summary: |-
  The 16 shipped skills carry frontmatter descriptions totaling ~8.1 KB
  (~2,000 tokens). Hosts inject every description into every session's
  system prompt, so consumers pay for the full catalog on every API call
  and every prompt-cache re-write — for text whose only job is routing
  the "when to load this skill" decision. Cap descriptions at ~300 chars
  and move trigger detail into the on-demand skill bodies.
definition_of_done: |
  - [ ] TDD: a regression test fails when any `goc/templates/skills/*/SKILL.md` frontmatter description exceeds the cap (~300 chars) — red on today's 868-char advance-card before the rewrite, green after.
  - [ ] MECHANICAL: every shipped skill description rewritten to ≤ ~300 chars with the strongest 2–4 AUTO-INVOKE cues retained; exhaustive trigger enumerations moved into the skill body; mirrors re-synced via the pre-commit sync.
  - [ ] EMPIRICAL: total description size before/after recorded in log.md (baseline 8,128 chars ≈ 2,032 tokens; expect ≤ ~50% of that).
worker: {who: "claude[bot]", where: main}
---

# Skill descriptions bloat every consumer session prompt

## Location

`goc/templates/skills/*/SKILL.md` frontmatter `description:` fields (source
of truth; auto-synced into `claude-plugin/`, `codex-plugin/`,
`openclaw-plugin/`, and consumer installs).

## What's broken

Skill hosts (Claude Code, Codex, OpenClaw) build a skill catalog by
injecting every installed skill's `name` + `description` into the system
prompt of **every session** — whether or not the session ever touches GoC.
The description's only functional job at that point is to let the model
decide *when to load* the SKILL.md body. The shipped descriptions instead
carry near-complete usage manuals. Measured on the shipped plugin payload
(v0.0.24), all 16 skills:

| chars | skill |
|---|---|
| 868 | advance-card |
| 698 | upgrade |
| 622 | audit-deck |
| 578 | create-card |
| 565 | refine-deck |
| 536 | retrospective |
| 519 | scan-deck |
| 473 | card-schema |
| 471 | decide-card |
| 469 | next-card |
| 441 | kickoff |
| 437 | claude-kickoff |
| 397 | finish-card |
| 389 | standup |
| 383 | deck |
| 282 | pull-card |

**Total: 8,128 chars ≈ 2,032 tokens** in every consumer session prompt.

`advance-card` (868 chars) illustrates the pattern — an exhaustive
AUTO-INVOKE enumeration inside the description:

> "… AUTO-INVOKE when user says "I'll start on X", "I'm working on",
> "mark this disproved", "supersede with Z", "this is part of X", "make
> this depend on Y", "these should be linked", "should this be an edge or
> a tag?", "remove this dependency", "unlink these", …"

Three or four of those cues would route the load decision just as
reliably; the rest is body material that is already (or belongs) in the
SKILL.md, which hosts load on demand.

## Why it matters

The catalog is static prompt-prefix: it is re-read on every API call of
every session, and on Anthropic-billed models it is also re-paid on every
prompt-cache write (new session, idle TTL expiry, context-edit
invalidation). On a measured consumer install with a large skill set, the
full catalog was ~11k tokens of a ~60k static prefix — with GoC
contributing ~2k tokens (~18 %) despite being routing metadata only.
Across a fleet of always-on agents this is a permanent per-turn tax that
buys no capability: the methodology lives in the bodies, not the catalog.

## Fix

1. Rewrite each `goc/templates/skills/*/SKILL.md` description to
   ≤ ~300 chars: one sentence of purpose + the 2–4 strongest AUTO-INVOKE
   cues + cross-skill disambiguation where load-bearing (e.g.
   advance-card vs finish-card). Move exhaustive trigger-phrase lists
   into the top of the skill body.
2. Add a regression test (alongside the existing template/mirror parity
   tests) that fails when a shipped skill's description exceeds the cap,
   so new skills stay lean. Add it **before** the rewrite (red on
   advance-card's current 868 chars), then make it green.
3. Edit templates only — the pre-commit `sync-plugin-assets` hook
   regenerates the plugin mirrors; `port_skills_to_openclaw.py` re-port
   for the OpenClaw payload.
