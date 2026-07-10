---
title: upgrade-briefing-fallback-moves-gitignored-claude-local-home-into-agents-md
summary: "The briefing home chosen at install time is persisted nowhere; upgrade re-detects it by grepping on-disk files for the GoC marker block. A repo installed with --briefing-target CLAUDE.local.md (gitignored by design) has no marker block on a fresh clone, so the resolver falls back to AGENTS.md and _sync_claude_import rewrites CLAUDE.md's @CLAUDE.local.md pointer to @AGENTS.md — silently reversing the user's keep-it-out-of-the-repo choice and producing a commit-ready diff that publishes the briefing."
status: open
stage: null
contribution: medium
created: "2026-07-09T01:13:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — on a fresh-clone shape (CLAUDE.md = `@CLAUDE.local.md`, no CLAUDE.local.md on disk) upgrade resolves the briefing home to CLAUDE.local.md or refuses without a prompt, and never retargets the import to @AGENTS.md
  - [ ] TDD: regression test for the chosen mechanism (pointer inference, persisted config key, or prompt)
  - [ ] MECHANICAL: the surviving-evidence rule is documented where the briefing-target feature is described (install help / AGENTS briefing)
  - [ ] PROCESS: decision on the resolution mechanism recorded below and in log.md
---

# `goc upgrade` on a fresh clone silently relocates a gitignored CLAUDE.local.md briefing into checked-in AGENTS.md

## Location

- `goc/install.py:1629-1630` (`_resolve_upgrade_briefing_target`, the `len(found) == 0` fallback)
- `goc/install.py:143-158` (`_detect_briefing_targets_on_disk` — on-disk marker grep is the only evidence source)
- `goc/install.py:247-250` (`_sync_claude_import` — treats any `@<importable-target>` line as GoC-owned and rewrites it)

## What's broken

The briefing home chosen at install time (`--briefing-target
CLAUDE.local.md`, the option whose help text sells it as gitignored)
is persisted nowhere — `config.yaml` has no key for it. On upgrade the
home is re-derived purely from on-disk marker blocks:

```python
    found = _detect_briefing_targets_on_disk(target)
    if len(found) == 1:
        return found[0]
    if len(found) == 0:
        return DEFAULT_BRIEFING_TARGET
```

On a fresh clone the gitignored `CLAUDE.local.md` is absent, so
`found` is empty and the resolver silently returns `AGENTS.md` — even
though the checked-in `CLAUDE.md` still carries the surviving
evidence `@CLAUDE.local.md`. The upgrade then writes the full GoC
marker block into a checked-in `AGENTS.md`, and `_sync_claude_import`
rewrites the pointer:

```python
    if not stripped or stripped in import_lines:
        _write_text_keep_newline(claude_md, import_line + "\n", newline)
```

`@CLAUDE.local.md` is in `import_lines`, so `CLAUDE.md` becomes
`@AGENTS.md`.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/upgrade-briefing-fallback-moves-gitignored-claude-local-home-into-agents-md/reproduce.py
resolved briefing home: AGENTS.md
CLAUDE.md after upgrade sync: '@AGENTS.md'
DEFECT: upgrade on a fresh clone relocates the gitignored CLAUDE.local.md briefing into checked-in AGENTS.md and retargets the CLAUDE.md import
exit=1
```

## Why it matters

The user picked `CLAUDE.local.md` precisely to keep GoC guidance out
of the repository. Any collaborator's fresh clone — or CI running
`goc upgrade --keep-local-skills`, which defeats the same-version
short-circuit (`install.py:1752-1761`) — reverses that explicit
configuration with no prompt or warning and leaves a commit-ready
diff that publishes the briefing into version control. Reachability
is the ordinary upgrade flow; no exotic input is needed, just a
clone that respects `.gitignore`.

Related but distinct:
[kickoff-asks-where-goc-briefing-lives](../kickoff-asks-where-goc-briefing-lives/)
introduced the three-home feature and documents `CLAUDE.local.md` as
"not checked in" without covering the absent-home upgrade path;
[sync-claude-import-overwrites-user-authored-import-line-with-goc-target](../sync-claude-import-overwrites-user-authored-import-line-with-goc-target/)
covers user-authored import lines — this card is the resolver's
fallback feeding a wrong-but-GoC-shaped target into that same sync.

## Decision required

Which evidence should the zero-marker-blocks branch trust, given the
home file itself may legitimately be absent?

1. **Pointer inference:** if `CLAUDE.md` consists of a GoC-shaped
   import line `@<importable-target>`, treat that target as the home
   and scaffold it fresh (it is gitignored, so writing it is safe and
   local). Zero new state; fixes the fresh-clone case exactly.
2. **Persist the choice:** write a `briefing_target:` key into
   `.game-of-cards/config.yaml` at install time and read it on
   upgrade; on-disk detection becomes the legacy fallback. More
   robust (survives a user emptying CLAUDE.md) but adds a config key
   and a migration story for existing installs.
3. **Prompt instead of defaulting:** when zero marker blocks are
   found but a `@CLAUDE.local.md` pointer exists, ask (and in
   `--keep-local-skills` / headless mode, refuse to relocate). Safest
   but adds an interactive branch to a path that must also run
   headless.

Options 1 and 2 compose (persist going forward, infer for legacy
installs); a pick is needed before implementation.
