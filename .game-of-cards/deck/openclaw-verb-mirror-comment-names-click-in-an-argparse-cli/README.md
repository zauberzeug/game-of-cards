---
title: openclaw-verb-mirror-comment-names-click-in-an-argparse-cli
summary: "`openclaw-plugin/index.ts:44` introduces the GOC_VERBS mirror contract with \"Mirrors the click subparser surface in goc/cli.py\" while the very next line says \"The argparse `commands` field is the source of truth.\" GoC has never used click. The contradiction sits on the comment whose only job is telling future editors where to re-sync the verb list from."
status: active
stage: null
contribution: low
created: "2026-07-26T08:09:35Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [ ] MECHANICAL: the comment at `openclaw-plugin/index.ts:44` names one framework, and it is argparse — a reader grepping the repo for the named framework finds the parser it points at.
  - [ ] MECHANICAL: `openclaw-plugin/dist/index.js` + `index.js.map` are rebuilt (`cd openclaw-plugin && npm ci && npm run build`) and committed alongside the source edit, so the committed bundle still corresponds to its source.
  - [ ] PROCESS: `python scripts/sync_plugin_assets.py --check` and `uv run python -m unittest discover -s tests` stay green.
worker: {who: "claude[bot]", where: main}
---

# The OpenClaw verb-mirror comment names click in a CLI that uses argparse

## Location

`openclaw-plugin/index.ts:44-45`

## What's broken

```ts
// Mirrors the click subparser surface in goc/cli.py — keep in sync when new
// verbs land. The argparse `commands` field is the source of truth.
const GOC_VERBS = [
```

Two consecutive lines name two different CLI frameworks. `argparse` is right:
`goc/cli.py` builds the parser via `engine._build_parser`, and `engine.py` uses
`argparse` throughout. `click` is not a dependency and appears in no Python
source or packaging file:

```
$ grep -ril click goc/*.py goc/_vendor/*.py scripts/*.py pyproject.toml
(no matches)
```

(The one repo-wide hit, `goc/templates/skills/create-card/reference.md:139`, is
the English verb: "clicking a `.html` link shows source on github.com".)

The verb list itself is currently correct — all 17 entries match the engine's
subparsers — so this is a comment defect, not a drift defect. (The separate
absence of `install` / `upgrade` from `GOC_VERBS` is already tracked by
[`openclaw-plugin-goc-tool-cannot-call-install-or-upgrade-verbs`](../openclaw-plugin-goc-tool-cannot-call-install-or-upgrade-verbs/).)

## Why it matters

This comment exists for exactly one purpose: telling a future editor where to
re-derive `GOC_VERBS` when a verb lands. Naming a framework the project does
not use sends that editor grepping for a click command group that isn't there,
and undercuts the credibility of the mirror contract at the one place a reader
consults it. The repo has a track record of `GOC_VERBS` falling behind the
engine — see the closed
[`openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs`](../openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs/)
— so the instruction being followable is not cosmetic.

## Fix

Drop `click` from the first sentence: "Mirrors the argparse subparser surface
in `goc/cli.py` — keep in sync when new verbs land. `engine._build_parser` is
the source of truth."

**Not a one-line change in practice.** `openclaw-plugin/dist/index.js` is a
committed build artifact and the file the OpenClaw runtime actually loads, so
any `index.ts` edit obliges `npm ci && npm run build` and a commit of the
regenerated bundle. Nothing in the repo enforces that today — see
[`openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry`](../openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry/).
Whoever claims this card needs Node and network available; a session without
them should leave the card open rather than land a source edit with a stale
`dist/`.
