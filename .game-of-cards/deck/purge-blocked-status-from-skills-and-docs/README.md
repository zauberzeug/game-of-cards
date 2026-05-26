---
title: purge-blocked-status-from-skills-and-docs
summary: |-
  Decomposition of `remove-blocked-from-status-enum-…`: the docs/skills
  half. Stop recommending `status: blocked` and document the three-axis
  model (progress status / derived dependency-readiness / stored
  impediment overlay) across the skill bodies and AGENTS files, then
  re-sync plugin mirrors. Soft-deprecation: this lands BEFORE the enum
  value is removed, steering authors off `blocked` while it's still
  technically accepted — so it's autonomous-pull-safe and doesn't break
  validation.
status: active
stage: null
contribution: medium
created: "2026-05-26T12:11:27Z"
closed_at: null
human_gate: none
advances:
  - remove-blocked-from-status-enum-and-migrate-existing-cards
advanced_by: []
tags: [documentation]
definition_of_done: |
  - [ ] `advance-card` skill: the `* → blocked` transition row is
        removed; replaced with guidance to set the impediment overlay
        (`goc wait …` / `waiting_on`) for hard "can't start yet" waits,
        or rely on derived dependency-readiness for prereq waits.
  - [ ] `card-schema` skill: the status lifecycle documents the
        three-axis model (progress status; derived dependency readiness;
        stored impediment overlay) and marks `blocked` as deprecated /
        being removed; `STALE_BLOCKED` / `ORPHAN_BLOCKED` references are
        reconciled in prose (they become migration aids, not steady
        state).
  - [ ] `deck` skill lifecycle diagram + `templates/AGENTS_GOC.md` and
        this repo's `AGENTS.md` describe the model without `blocked` as
        a first-class status.
  - [ ] Plugin mirrors re-synced (`python scripts/sync_plugin_assets.py`)
        and `goc validate` + the sync `--check` are green.
  - [ ] Edits are forward-compatible with the enum still accepting
        `blocked` (this card soft-deprecates in docs; the enforced
        removal is the sibling
        `remove-blocked-from-the-status-enum-and-validator`).
worker: {who: "claude[bot]", where: main}
---

# Purge `blocked` from skills and AGENTS docs

Decomposition of the breaking epic
[`remove-blocked-from-status-enum-and-migrate-existing-cards`](../remove-blocked-from-status-enum-and-migrate-existing-cards/).
This is the **documentation half**, extracted so it can drain
autonomously. It rewrites the guidance to the three-axis model and
soft-deprecates `blocked` — safe to land before the enum value is
actually removed, because steering authors away from a still-accepted
value breaks nothing.

## Why separate from the enum removal

The enforced removal (drop from `status_values`, validator rejects it)
is breaking and release-coordinated — it's the gated sibling
[`remove-blocked-from-the-status-enum-and-validator`](../remove-blocked-from-the-status-enum-and-validator/).
Docs can lead the code here: "stop using `blocked`; use derived
readiness or `waiting_on`" is correct guidance even while the enum
still technically accepts the value. Landing docs first means that when
the removal does land, the guidance is already in place.

## Surfaces

`advance-card`, `card-schema`, `deck` skill bodies (source under
`goc/templates/skills/…` — edit the template, the sync hook mirrors to
`.claude`/`.codex`/plugins), `templates/AGENTS_GOC.md`, and this repo's
`AGENTS.md`. Per repo convention, never edit the `.claude/skills` /
plugin copies directly.
