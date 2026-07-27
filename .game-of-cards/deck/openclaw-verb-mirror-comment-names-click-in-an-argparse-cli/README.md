---
title: openclaw-verb-mirror-comment-names-click-in-an-argparse-cli
summary: "`openclaw-plugin/index.ts:44` introduces the GOC_VERBS mirror contract with \"Mirrors the click subparser surface in goc/cli.py\" while the very next line says \"The argparse `commands` field is the source of truth.\" GoC has never used click. The contradiction sits on the comment whose only job is telling future editors where to re-sync the verb list from."
status: done
stage: null
contribution: low
created: "2026-07-26T08:09:35Z"
closed_at: "2026-07-26T08:20:14Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [documentation, infra]
definition_of_done: |
  - [x] MECHANICAL: the comment at `openclaw-plugin/index.ts:44` names one framework, and it is argparse — a reader grepping the repo for the named framework finds the parser it points at.
  - [x] MECHANICAL: `openclaw-plugin/dist/index.js` + `index.js.map` are rebuilt (`cd openclaw-plugin && npm ci && npm run build`) and committed alongside the source edit, so the committed bundle still corresponds to its source.
  - [x] PROCESS: `python scripts/sync_plugin_assets.py --check` and `uv run python -m unittest discover -s tests` stay green.
  - [x] TDD (added at closure): a regression guard keeps the comment honest — `tests/test_guidance_accuracy.py::CliFrameworkPointerAccuracyTest` is red on the pre-fix `index.ts` and green after. The original DoD made the naming a one-time edit; the repo's existing doc-accuracy-guard family makes it enforceable for the same few lines.
worker: {who: "claude[bot]", where: main}
---

# The OpenClaw verb-mirror comment names click in a CLI that uses argparse

**FIXED** — see `## Fix (applied)`.

**Generalization:** this was the eighth instance of one shape — a claim
restating tree state with no guard, found only after it had already rotted. The
architectural card is
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
(`human_gate: decision` — it needs a scope pick). This instance is the one that
shows per-*surface* guarding is the wrong unit: its stale claim was the *same*
falsehood the second instance already guarded (`AgentsArchitectureAccuracyTest`,
2026-05-27, "goc's CLI is not click"), which had sat unguarded in a second file
for two months. No `advances` edge: that card closes on its own deliverable, so
it is a governing cluster, not an aggregation epic.

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

## Fix (applied)

The comment names argparse only, and points at the parser it actually mirrors:

```ts
// Mirrors the argparse subparser surface that `_build_parser` registers in
// goc/engine.py (goc/cli.py wires that parser up) — keep in sync if new verbs
// land. That parser is the source of truth; the drift guard in
// tests/test_plugin_mirror_parity.py fails the build on any mismatch.
```

Dropping `click` was only half of it: the second sentence's pointer was
unresolvable too. There is no argparse `commands` field — the subparsers
register under `dest="command"` (`goc/engine.py:3463`), and the list an editor
must re-derive `GOC_VERBS` from is `_build_parser` (`goc/engine.py:3404`).
Both halves now resolve to real code, and naming the existing drift guard
(`tests/test_plugin_mirror_parity.py::OpenClawToolVerbSurfaceTest`) tells the
editor the mirror contract is machine-enforced rather than honour-system.

A guard for the comment itself was added alongside:
`tests/test_guidance_accuracy.py::CliFrameworkPointerAccuracyTest` asserts
`openclaw-plugin/index.ts` never names Click. It is red on the pre-fix file
(`git show HEAD~1:openclaw-plugin/index.ts` matches `/click/i` at line 44) and
green after.

### Rebuild outcome

`npm ci && npm run build` regenerated the bundle. `dist/index.js` came back
**byte-identical** — esbuild strips comments, so a comment-only source edit
never reaches the bundle — and only `dist/index.js.map` changed, because the
sourcemap embeds the original TypeScript in `sourcesContent`. The committed
bundle therefore still corresponds to its source. The general absence of a
build-drift guard remains tracked by
[`openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry`](../openclaw-plugin-compiled-dist-drifts-silently-from-its-typescript-entry/);
this session confirmed the toolchain is reproducible — `npm ci` on a clean
checkout rebuilt the committed `dist/` with no diff before any source edit.
