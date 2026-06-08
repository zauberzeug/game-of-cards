---
title: release-fixed-skill-frontmatter-to-codex-plugin-cache
summary: "The strict-YAML skill frontmatter fix is present on `origin/main`, but Codex still loads the old unquoted payload from the versioned `game-of-cards/0.0.23` plugin cache. Ship a patch release so plugin managers receive a new version key whose skill files contain the fixed quoted frontmatter."
status: open
stage: null
contribution: high
created: "2026-06-07T08:25:25Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - skill-frontmatter-descriptions-break-yaml-loading
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] EMPIRICAL: The local `0.0.23` Codex plugin cache is confirmed to contain the old unquoted skill frontmatter, while `origin/main` contains the quoted fix.
  - [ ] TDD: `uv run python -m unittest tests.test_skill_frontmatter_strict_yaml` passes before release dispatch.
  - [ ] EMPIRICAL: A new patch release is dispatched from `origin/main` with a version greater than `0.0.23`, and the run URL / identifier is recorded in `log.md`.
  - [ ] EMPIRICAL: The release tag or checked-in release-bump commit contains quoted frontmatter for `kickoff`, `advance-card`, `pull-card`, and `next-card` in the plugin payload.
  - [ ] PROCESS: The closed source-fix card records a forward pointer to this release-propagation follow-up.
---

# Release fixed skill frontmatter to Codex plugin cache

## Location

- Published / cached payload:
  `/Users/rodja/.codex/plugins/cache/zauberzeug-claude/game-of-cards/0.0.23/skills/`
- Fixed source-of-truth templates:
  `goc/templates/skills/{kickoff,advance-card,pull-card,next-card}/SKILL.md`
- Fixed generated plugin payloads:
  `claude-plugin/skills/` and `codex-plugin/skills/`
- Prior source-fix card:
  [skill-frontmatter-descriptions-break-yaml-loading](../skill-frontmatter-descriptions-break-yaml-loading/)

## What's broken

The source defect from the prior card is fixed in this repository and on
`origin/main`, but Codex still starts with a cached plugin payload under the
`0.0.23` version directory. That cached payload predates the fix and still has
plain YAML frontmatter scalars containing nested `: ` text. Codex's strict
frontmatter loader rejects those files before the skill bodies can load.

This is not a new template-parser bug. It is a release / cache propagation
gap: the fixed payload needs to be published under a new plugin version so
Codex has a cache key that is not the stale `0.0.23` directory.

## Empirical evidence

Current cache inspection shows the stale shape in the installed plugin cache:

```yaml
description: Kick off GoC in a fresh repo ... Host-agnostic: per-host complements ...
description: Pull the highest-leverage `human_gate: none` open card ...
argument-hint: <title> <new-status: active|open|disproved|superseded> [--by <other-title>]
```

Current repository inspection shows the fixed shape in source and generated
payloads:

```yaml
description: "Kick off GoC in a fresh repo ... Host-agnostic: per-host complements ..."
description: "Pull the highest-leverage `human_gate: none` open card ..."
argument-hint: "<title> <new-status: active|open|disproved|superseded> [--by <other-title>]"
```

`git log v0.0.23..origin/main` includes:

```text
2f1ba0a fix(skills): quote strict-yaml frontmatter - closes skill-frontmatter-descriptions-break-yaml-loading
```

## Why it matters

The skipped skills include onboarding, queue selection, autonomous pulling,
and card status / edge mutation. A user can have a correct local checkout but
still start Codex with a broken plugin cache if the plugin manager resolves
the latest available version as `0.0.23`.

## Fix

Dispatch the canonical release workflow for the next patch version:

```bash
gh workflow run release.yml -f version=0.0.24
```

Then verify that the release-bump commit or tag contains the quoted
frontmatter in the shipped plugin payload. If the release fails after tag
creation, recover through the documented tag-mode rerun:

```bash
gh workflow run release.yml --ref v0.0.24
```
