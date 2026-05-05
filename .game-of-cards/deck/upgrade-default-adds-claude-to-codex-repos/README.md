---
title: upgrade-default-adds-claude-to-codex-repos
summary: "A no-flag `goc upgrade` in an older Codex-only install defaults to `agents: claude` instead of detecting the existing Codex harness. The upgrade path can add Claude-only files to Codex repos and skip refreshing `.codex/skills` unless the user remembers `--agents codex`."
status: done
stage: null
contribution: high
created: 2026-05-04
closed_at: 2026-05-05
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `uv run python deck/upgrade-default-adds-claude-to-codex-repos/reproduce.py` exits zero
  - [x] No-flag `goc upgrade` detects existing installed agent surfaces the same way install does
  - [x] A Codex-only install upgrades Codex assets by default and does not plan Claude-only writes unless Claude is present or explicitly requested
  - [x] Regression coverage exercises no-flag upgrade in Codex-only, Claude-only, and mixed installs
---

# upgrade-default-adds-claude-to-codex-repos

## Location

- `goc/install.py:474`
- `goc/install.py:537`
- `goc/install.py:551`
- `goc/install.py:552`
- `docs/cli.md:71`

## What's broken

`goc install` auto-detects existing agent surfaces before choosing the
default harness:

```python
detected_agents = _detect_agent_surfaces(target, supported_agents=supported_agents)
default_agents = detected_agents or _default_install_agents(target, supported_agents=supported_agents)
```

`goc upgrade` does not. It passes the hard-coded default:

```python
agents = _parse_agents(
    agent_specs,
    claude=claude_flag,
    codex=codex_flag,
    supported_agents=_registered_agents(templates),
    default_agents=DEFAULT_AGENTS,
)
```

The CLI guide advertises no-flag upgrade as the basic command:

```bash
goc upgrade
```

In a Codex-only repo with an older `.goc-version`, that no-flag command
plans `agents: claude`.

## Empirical evidence

Current output from `uv run python deck/upgrade-default-adds-claude-to-codex-repos/reproduce.py`:

```text
install_exit=0
installed_codex=True
installed_claude=False
upgrade_exit=0
goc upgrade would sync 0.0.1 → 0.0.3
goc upgrade (dry-run) — agents: claude — 31 writes planned
  shared sync   deck/.goc-version
  shared sync   .game-of-cards/tooling-conventions.md
  shared sync   .game-of-cards/documentation-conventions.md
  shared sync   .game-of-cards/domain-examples.md
  shared sync   .game-of-cards/config.yaml
  shared sync   .game-of-cards/file-path-map.md
defect present: no-flag upgrade in a Codex-only repo plans Claude
```

## Why it matters

Codex harness installation intentionally avoids Claude-only skills and
hooks. A normal version upgrade should preserve that installed surface.
Instead, Codex users who follow the advertised `goc upgrade` command can
get `.claude/skills` and Claude hooks added unexpectedly, while their
existing `.codex/skills` tree is not refreshed unless they know to pass
`--agents codex`.

## Fix

Make `upgrade` choose defaults from existing installed surfaces, matching
the install behavior. If no surface is detectable, fall back to the
documented default. Keep explicit `--agents`, `--claude`, and `--codex`
overrides authoritative.
