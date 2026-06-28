---
title: codex-startup-loads-yaml-broken-plugin-cache
summary: "Codex still emitted invalid-YAML warnings after the v0.0.24 GoC release because the user's enabled plugin was `game-of-cards@zauberzeug-claude`, whose marketplace snapshot pins `zauberzeug/game-of-cards` at `v0.0.23`. Installing the direct `game-of-cards@game-of-cards` marketplace payload and removing the stale `@zauberzeug-claude` entry moves Codex to the strict-YAML-safe 0.0.24 cache."
status: done
stage: null
contribution: high
created: "2026-06-08T05:31:38Z"
closed_at: "2026-06-08T11:56:34Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] EMPIRICAL: `reproduce.py` exits zero and reports that the enabled Codex GoC plugin is `game-of-cards@game-of-cards` with version >= 0.0.24.
  - [x] EMPIRICAL: local Codex config no longer enables `game-of-cards@zauberzeug-claude`.
  - [x] EMPIRICAL: the active 0.0.24 plugin-cache skill frontmatter has no strict-YAML hazards from unquoted `: ` scalars.
  - [x] MECHANICAL: `goc/templates/skills/codex-kickoff/SKILL.md` documents the migration path from stale `zauberzeug-claude` installs to the direct marketplace.
  - [x] PROCESS: plugin mirrors regenerated and `uv run python -m unittest tests.test_skill_frontmatter_strict_yaml` / `uv run goc validate` pass.
---

# Codex startup loads YAML-broken plugin cache

## Location

- Local stale marketplace snapshot:
  `/Users/rodja/.codex/.tmp/marketplaces/zauberzeug-claude/.claude-plugin/marketplace.json:23-29`
- Local stale plugin cache:
  `/Users/rodja/.codex/plugins/cache/zauberzeug-claude/game-of-cards/0.0.23/skills/`
- Local fixed plugin cache:
  `/Users/rodja/.codex/plugins/cache/game-of-cards/game-of-cards/0.0.24/skills/`
- Source guidance:
  `goc/templates/skills/codex-kickoff/SKILL.md`

## What's broken

The strict-YAML skill-frontmatter fix was released in `game-of-cards`
`v0.0.24`, but Codex startup still warned about invalid YAML because the
enabled plugin was not loaded from this repository's direct Codex
marketplace. The enabled entry was `game-of-cards@zauberzeug-claude`.

That separate marketplace still pinned GoC to the old Claude-plugin
payload:

```json
{
  "name": "game-of-cards",
  "source": {
    "source": "git-subdir",
    "url": "https://github.com/zauberzeug/game-of-cards.git",
    "path": "claude-plugin",
    "ref": "v0.0.23"
  }
}
```

The pinned `v0.0.23` cache contains unquoted frontmatter values with
nested mapping-colon text. Codex's strict YAML loader rejects those
files at startup before the GoC skills can load.

## Empirical evidence

Before the local fix, the only installed GoC plugin cache was:

```text
/Users/rodja/.codex/plugins/cache/zauberzeug-claude/game-of-cards/0.0.23
```

The stale cache included strict-YAML-invalid skill frontmatter such as:

```yaml
description: Pull the highest-leverage `human_gate: none` open card off the queue, claim it, work it, close it, commit.
argument-hint: <title> <new-status: active|open|disproved|superseded> [--by <other-title>]
```

The repository and the direct upstream plugin payload were already fixed:

```text
uv run python -m unittest tests.test_skill_frontmatter_strict_yaml
..
OK

uv run python .game-of-cards/deck/skill-frontmatter-descriptions-break-yaml-loading/reproduce.py
OK — shipped skill frontmatter avoids unquoted nested mapping-colon scalars.
```

Remote evidence on 2026-06-08 confirmed that GitHub has tag `v0.0.24`
and that `main`'s `codex-plugin/.codex-plugin/plugin.json` reports
version `0.0.24`.

## Why it matters

The prior release card correctly shipped `v0.0.24`, but the user's
actual Codex startup path continued through a different marketplace
that pinned the old tag. That makes the issue look like a failed
release even though the release artifact is correct. Future Codex setup
guidance needs to call out this migration path so users do not keep
loading `game-of-cards@zauberzeug-claude` after the direct
`game-of-cards@game-of-cards` marketplace exists.

## Fix

Local host repair:

```bash
codex plugin marketplace add zauberzeug/game-of-cards
codex plugin add game-of-cards@game-of-cards
codex plugin remove game-of-cards@zauberzeug-claude
```

After that change, `~/.codex/config.toml` enables only
`[plugins."game-of-cards@game-of-cards"]`, and the installed plugin root is:

```text
/Users/rodja/.codex/plugins/cache/game-of-cards/game-of-cards/0.0.24
```

Repository hardening: update the Codex kickoff skill to document the
same migration explicitly.

## Related

- [skill-frontmatter-descriptions-break-yaml-loading](../skill-frontmatter-descriptions-break-yaml-loading/)
- [release-fixed-skill-frontmatter-to-codex-plugin-cache](../release-fixed-skill-frontmatter-to-codex-plugin-cache/)
