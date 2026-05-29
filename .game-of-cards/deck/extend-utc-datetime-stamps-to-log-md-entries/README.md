---
title: extend-utc-datetime-stamps-to-log-md-entries
summary: |-
  Card frontmatter records `created` and `closed_at` as ISO 8601 UTC datetime
  since the predecessor migration, but `log.md` event entries (rename,
  decision-recorded, closure-verification) and the body decision section
  still serialize as `YYYY-MM-DD`. Same-day events therefore lose their
  ordering inside the narrative trail. Extend the datetime treatment to every
  engine-written log header so an agent reading log.md can reconstruct the
  intra-day sequence without git timestamps.
status: done
stage: null
contribution: medium
created: "2026-05-14T11:25:45Z"
closed_at: "2026-05-14T11:31:34Z"
human_gate: none
advances: []
advanced_by:
  - record-card-timestamps-as-utc-datetime
tags: [meta-fix, documentation]
definition_of_done: |
  - [x] `_cmd_move` writes UTC datetime in the rename log-entry header
  - [x] `_cmd_decide` writes UTC datetime in both the body `## Decision`
        section and the log-entry header
  - [x] `_cmd_attest` writes UTC datetime in the `## Closure verification
        (...)` block header
  - [x] `_run_derived_check`'s `log-md-closure-entry` branch matches a
        date-prefix on the closure header so legacy and datetime forms
        both validate
  - [x] `finish-card` skill template (`goc/templates/skills/finish-card/SKILL.md`)
        documents the new datetime closure-header form
  - [x] `uv run goc validate` passes on this repo's deck
  - [x] `python scripts/sync_plugin_assets.py` leaves no drift
worker: {who: "claude[bot]", where: main}
---

# extend-utc-datetime-stamps-to-log-md-entries

## What's missing

The predecessor card `record-card-timestamps-as-utc-datetime` upgraded
the two frontmatter fields (`created`, `closed_at`) to ISO 8601 UTC
datetime. The log.md narrative — which records events with strictly
finer granularity than the card itself — still serializes as
`YYYY-MM-DD`. Concrete sites in `goc/engine.py`:

- `_cmd_move` (rename) — line 2862,2866: `## {today}: renamed from <old>`
- `_cmd_decide` — line 2890: passes date to `replace_or_append_decision`
  (body) and writes `## {today}: decision recorded` to log.md
- `_cmd_attest` — line 2434: passes date to `_format_attestation_block`,
  which writes `## Closure verification ({today})` to log.md
- `_run_derived_check` `log-md-closure-entry` — line 2377: reads
  log.md and matches `## {today} — Closure` exactly

## Why it matters

The frontmatter migration solved sort order for card lifecycle events
(file → close). The same argument applies inside a single card's
log.md: decisions, renames, and attestation runs can land in the same
day. A reader (human or agent) using log.md as the authoritative
narrative has no way to reconstruct their order from the document
itself.

The lexicographic-compatibility property still holds — date and
datetime strings sort cleanly against each other — so legacy log.md
entries continue to read correctly without rewrite.

## Decision

*Resolved 2026-05-14:* Engine-written log.md headers and the body
`## Decision` section move to UTC datetime; the human-authored
`## YYYY-MM-DD — Closure` header in the `finish-card` skill flips to
the datetime form too, and the derived check loosens to a
date-prefix match so legacy entries keep validating.

*Reasoning:* uniform treatment with the frontmatter migration; closing
agent is an LLM that can format a datetime as easily as a date;
date-prefix match is robust against the second-or-two skew between
when the closer wrote the marker and when `goc attest` runs.

## Notes

- No backfill of existing log.md entries; the validator must remain
  tolerant of the legacy date-only form.
- UTC only — local offsets break lexicographic sort and were rejected
  by the predecessor migration on the same grounds.
- Skill content under `goc/templates/skills/` is the source of truth;
  the `sync-plugin-assets` pre-commit hook mirrors it to
  `claude-plugin/skills/` and the OpenClaw skill copies are
  hand-ported separately.
