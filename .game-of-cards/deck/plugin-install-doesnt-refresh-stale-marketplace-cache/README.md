---
title: plugin-install-doesnt-refresh-stale-marketplace-cache
summary: "Document — and ideally automate — the workaround for Claude Code's `/plugin install` not refreshing the marketplace clone, so consumers updating to a newer plugin version don't silently get the cached old bytes."
status: done
stage: null
contribution: medium
created: 2026-05-07
closed_at: 2026-05-07
human_gate: none
advances:
  - add-plugin-update-instructions-to-marketplace-readme
advanced_by: []
tags: [story, bug, documentation]
definition_of_done: |
  - [x] README.md `Plugin install` section documents the refresh sequence: `/plugin marketplace update zauberzeug/game-of-cards` (or remove + re-add) BEFORE `/plugin install` for any version after the first
  - [x] llms.txt mirrors the same guidance in its "Lean alternative for Claude Code" section so LLM agents that direct users through plugin install also direct them through plugin update
  - [x] Bootstrap skill body adds a one-line note about the refresh idiom (so the LLM directing a consumer to `/plugin install` also surfaces `/plugin marketplace update` if a previous version is installed)
  - [x] Investigation notes whether Claude Code's `/plugin install` itself can be flagged via `/feedback` to auto-refresh the marketplace clone before installing — if there's a clean upstream fix, file that as the canonical resolution and treat the doc updates as the interim
---

# Plugin install doesn't refresh stale marketplace cache

## Why

The 2026-05-07 publish session hit this UX wall **three times in a row**:
after pushing a new commit to `zauberzeug/game-of-cards`, running

```
/plugin uninstall game-of-cards@game-of-cards
/plugin install game-of-cards@game-of-cards
```

does NOT refresh `~/.claude/plugins/marketplaces/game-of-cards/`.
Claude Code keeps installing from the stale clone, so consumers
updating after any post-release fix silently get the old bytes —
even though they explicitly reinstalled.

The actual refresh idiom is `/plugin marketplace update <name>` (or
`marketplace remove + add` round-trip) BEFORE `/plugin install`. This
is **not documented** in the install path we tell consumers about,
which means every existing user will hit the wall the first time
they update.

## Reproduction (manual, observed three times this session)

1. Install the plugin: `/plugin marketplace add zauberzeug/game-of-cards`,
   `/plugin install game-of-cards@game-of-cards` — works.
2. Push a fix to the plugin repo's default branch.
3. From a fresh Claude Code session: `/plugin uninstall ...`,
   `/plugin install ...`.
4. Inspect `~/.claude/plugins/marketplaces/game-of-cards/`: still at
   the old git SHA, missing the fix.
5. Inspect `~/.claude/plugins/cache/game-of-cards/.../<version>/`:
   reflects the old SHA's bytes.

The fix from the user side: `git -C ~/.claude/plugins/marketplaces/game-of-cards pull`
(or the slash-command equivalent `/plugin marketplace update game-of-cards`),
THEN reinstall.

## Scope

This card is **documentation + skill body update**, not a code
change to `goc`. The defect itself is in Claude Code's plugin
install machinery (a fix there would auto-refresh the marketplace
clone before installing); we work around it for now by teaching
both human users and LLM agents the right idiom.

## Notes

- Discovered while shipping `publish-claude-code-plugin` — every
  iteration of "push fix → reinstall → still broken" was a wasted
  cycle until Rodja realized the marketplace cache was stale.
- The byte-for-byte CI tripwire in `ci.yml` only catches
  symlink-strip-class regressions; it doesn't help with the
  consumer-side stale-cache UX.
- Consider filing a `/feedback` to Anthropic asking that
  `/plugin install` either auto-refresh or warn when the marketplace
  clone is older than N hours.

## Investigation: upstream /feedback path

No API or CLI mechanism exists to programmatically submit a `/feedback`
report to Anthropic — the slash command is Claude Code UI-only. The
cleanest upstream fix would be for Claude Code's `/plugin install` to
`git pull` the marketplace clone before extracting the plugin payload
(or at minimum warn when the clone is older than N hours).

This is a Claude Code product bug, not something we can fix in `goc`.
The interim mitigation documented in `goc.md`, `site/llms.txt`, and the
bootstrap skill body is the correct resolution until Anthropic addresses
it upstream. Filing a `/feedback` from Claude Code to report this
behavior to Anthropic is recommended — it surfaces the issue with
concrete reproduction steps from the card's `## Reproduction` section.
