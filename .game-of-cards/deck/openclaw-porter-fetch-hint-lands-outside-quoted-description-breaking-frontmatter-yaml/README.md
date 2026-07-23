---
title: openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml
summary: "The OpenClaw skill porter appends its tool-served fetch hint after the description line's closing double quote, so the shipped pull-card and next-card SKILL.md frontmatter is invalid YAML that any strict loader rejects. The strict-YAML regression test skips quoted scalars entirely, so CI stays green on the broken payload."
status: active
stage: null
contribution: high
created: "2026-07-23T13:17:29Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] (replace with real criteria)
worker: {who: "claude[bot]", where: main}
---

# openclaw-porter-fetch-hint-lands-outside-quoted-description-breaking-frontmatter-yaml

(write the design doc here)
