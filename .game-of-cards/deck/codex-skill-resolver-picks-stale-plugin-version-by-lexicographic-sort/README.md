---
title: codex-skill-resolver-picks-stale-plugin-version-by-lexicographic-sort
summary: "The Codex GoC command resolver appended to every Codex-normalized skill locates the bundled bootstrap with `find ... | sort | tail -n 1`, which sorts version path components lexicographically — `0.0.9` beats `0.0.27` and `0.0.100`. When an old plugin-cache version dir survives an upgrade (the documented real scenario), every Codex skill directs the agent to run the stale bundled engine. The hooks.json fallback already fixed this class with mtime (`ls -t | head -n 1`); the skill resolver was left behind."
status: done
stage: null
contribution: medium
created: "2026-07-17T01:07:16Z"
closed_at: "2026-07-17T01:16:49Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (resolver snippet picks the mtime-newest bootstrap, not the lexicographically-last version path)
  - [x] MECHANICAL: `CODEX_GOC_COMMAND_RESOLVER` in goc/install.py and the hand-written copy in goc/templates/skills/codex-kickoff/SKILL.md both use the mtime-based resolver
  - [x] MECHANICAL: `python scripts/sync_plugin_assets.py` re-run so all `.codex/skills/` and `codex-plugin/skills/` mirrors carry the fixed snippet; `--check` passes
  - [x] TDD: `uv run python -m unittest discover -s tests` passes
  - [x] MECHANICAL: `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# Codex skill resolver picks stale plugin version by lexicographic sort

## Location

- `goc/install.py:1126` — the `CODEX_GOC_COMMAND_RESOLVER` literal (single
  source for the "## Codex GoC Command" block that
  `scripts/sync_plugin_assets.py` and `goc install` append to every
  Codex-normalized skill — 30 committed mirrors under `.codex/skills/` and
  `codex-plugin/skills/`, plus every consumer repo's `.codex/skills/`).
- `goc/templates/skills/codex-kickoff/SKILL.md:115` — a hand-written copy of
  the same snippet.

## What's broken

The resolver fallback locates the bundled bootstrap across plugin-cache
version directories with:

```bash
GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 2>/dev/null | sort | tail -n 1)
```

`sort` is lexicographic over the versioned cache path
(`.../cache/<marketplace>/game-of-cards/<version>/skills/...`), so `0.0.9`
sorts after `0.0.27` and after `0.0.100`. The repo already diagnosed and
fixed this exact class in the Codex hook fallback
(`codex-plugin/hooks/hooks.json`, via the closed card
[codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions](../codex-plugin-upgrade-deletes-hook-scripts-under-running-sessions/)),
whose README states the contradicted contract:

> The fallback picks the newest surviving install **by mtime** (`ls -t`),
> not lexically — `0.0.100` sorts before `0.0.9` as a string.

The skill-body resolver was left on `sort | tail -n 1`.

## Empirical evidence

`reproduce.py` builds a fake cache with version dirs `0.0.9` (old mtime) and
`0.0.27` (new mtime) and runs the verbatim resolver pipeline from
`goc/install.py`. Pre-fix it printed `DEFECT CONFIRMED: lexicographic sort
selects the stale 0.0.9 over 0.0.27` (exit 1); with the applied fix:

```
resolver snippet from goc/install.py picks: .../game-of-cards/0.0.27/skills/_goc-bootstrap.sh
mtime-newest (expected): .../game-of-cards/0.0.27/skills/_goc-bootstrap.sh
OK: resolver selects the newest installed version
```

## Why it matters

Reachability: the closed hooks card documents that Codex plugin upgrades can
leave an old version dir alive in the cache while a session is running — the
same scenario makes the skill resolver's `find` see two version dirs. When
the surviving old dir has a lexicographically-larger version string (any
single-digit component vs a longer one, e.g. `0.0.9` vs `0.0.10+`), every
Codex GoC skill silently drives the deck with the *stale* bundled engine:
old schema, old verbs, old guards.

## Fix (applied)

Mirrors the hooks.json precedent — select by mtime instead of string order.
In `CODEX_GOC_COMMAND_RESOLVER` (goc/install.py:1126) and the codex-kickoff
template copy, `| sort | tail -n 1` is replaced with an mtime-newest pick:

```bash
GOC_BOOTSTRAP=$(find "$HOME/.codex/plugins/cache" -path '*/game-of-cards/*/skills/_goc-bootstrap.sh' -type f -perm -111 -exec ls -t {} + 2>/dev/null | head -n 1)
```

(`-exec ls -t {} +` is portable to BSD/macOS find, which lacks `-printf`.)
`python scripts/sync_plugin_assets.py` was re-run so all 30+ mirrors under
`.codex/skills/`, `codex-plugin/skills/`, and the bundled `goc/install.py`
copies carry the corrected snippet; `--check` passes.
