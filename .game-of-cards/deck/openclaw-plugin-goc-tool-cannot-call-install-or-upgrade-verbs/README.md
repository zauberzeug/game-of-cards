---
title: openclaw-plugin-goc-tool-cannot-call-install-or-upgrade-verbs
summary: "The OpenClaw plugin's registered `goc` tool constrains `verb` to a literal union that omits `install` and `upgrade`, while the plugin's own ported kickoff skills instruct the agent to run `goc install --briefing-target <file>`. The onboarding flow the plugin ships is unexpressible through the tool it ships, and the mirror-parity test structurally enforces the gap by pinning GOC_VERBS to the engine's subparser list (install/upgrade are cli.py-routed, not engine subparsers)."
status: open
stage: null
contribution: high
created: "2026-07-09T01:36:08Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded — which surface carries install/upgrade on OpenClaw (extend GOC_VERBS + parity contract, or an explicit non-tool recipe in the kickoff skills)
  - [ ] TDD: reproduce.py exits zero (the chosen surface can express `goc install`: either GOC_VERBS contains install/upgrade, or the ported kickoff skills no longer instruct a tool-unexpressible bare `goc install`)
  - [ ] TDD: tests/test_plugin_mirror_parity.py's verb-parity assertion matches the decided contract (engine subparsers plus any adjudicated cli.py-routed extras) and stays green
  - [ ] MECHANICAL: openclaw-plugin/skills/kickoff/SKILL.md and openclaw-kickoff/SKILL.md agree with the decided surface (re-ported from templates if the source changes)
  - [ ] MECHANICAL: `uv run goc validate` passes
---

# OpenClaw `goc` tool cannot call the `install`/`upgrade` verbs its own kickoff skills require

## Location

- `openclaw-plugin/index.ts:46-64` — `GOC_VERBS` literal union (17 verbs, no
  `install`, no `upgrade`); line 67 feeds it into `Type.Union` for the tool's
  `verb` parameter, so out-of-union verbs are rejected at input validation.
- `goc/cli.py:45` — `if argv and argv[0] in ("install", "upgrade"):` —
  install/upgrade are routed in `cli.py` *before* the engine parser, so they
  are not `_build_parser` subparsers.
- `tests/test_plugin_mirror_parity.py:557-568` —
  `test_ts_verbs_match_engine_subparsers` asserts `GOC_VERBS ==` engine
  subparser list **exactly**.

## What's broken

The tool schema:

```ts
const GOC_VERBS = [
  "validate", "quality-pass", "done", "attest", "status", "new", "wait",
  "advance", "unadvance", "repair-edges", "move", "decide", "publish",
  "triage", "show", "migrate", "migrate-list-style",
] as const;
```

The plugin's own ported onboarding skills, shipped in the same payload:

- `openclaw-plugin/skills/kickoff/SKILL.md:160` — "On confirmation, run
  `goc install --briefing-target <chosen file>`"
- `openclaw-plugin/skills/openclaw-kickoff/SKILL.md:94-96` — "Run from the
  OpenClaw plugin, `goc install` recognizes the host and scaffolds a
  no-harness layout … and never writes a `CLAUDE.md`."

On OpenClaw the registered tool is the only sanctioned `goc` surface — the
plugin README and `index.ts:16-19` note OpenClaw has **no auto-PATH-prepend**
for plugin binaries, so there is no bare `goc` on PATH unless the user
separately pipx-installed the package. A tool call with `verb: "install"`
fails typebox validation. Every fallback is worse:

- `exec` of bare `goc install` → ENOENT on a plugin-only host.
- A pipx-installed `goc install` runs *outside* the plugin payload, so
  `_is_openclaw_plugin_context()` (`goc/install.py:487-498`, keyed on
  `_PACKAGE_DIR.parent.name == "openclaw-plugin"`) is False and install
  defaults to the **Claude** harness — writing the `CLAUDE.md` import that
  `openclaw-kickoff` explicitly promises never appears ("No `CLAUDE.md`
  either").

The parity guard makes this structural: adding `install`/`upgrade` to
`GOC_VERBS` today fails `test_ts_verbs_match_engine_subparsers`, because that
test pins the union to `_build_parser`'s subparsers and install/upgrade are
deliberately argparse-independent (`goc/cli.py:45`). The closed card
[openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs](../openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs/)
established that parity contract for engine verbs but never adjudicated the
two cli.py-routed verbs.

## Why it matters

Reachability: fresh OpenClaw host → plugin install → user says "set up game
of cards" → `kickoff` Stage 4 instructs `goc install --briefing-target X` →
the agent calls the registered tool with `verb: "install"` (the ported
skills' own Context guidance says the subcommand maps to `verb`) → rejected
at validation. The plugin's first-run onboarding path dead-ends, or worse,
detours through a pipx engine that scaffolds the wrong (Claude) harness
layout, directly contradicting the shipped skill text.

Note `python3 -m goc.cli install` *works* when invoked with the plugin's
PYTHONPATH — the tool handler already runs exactly that command line for
every other verb. The schema union is the only blocker.

## Decision required

Two credible fix paths; a human should pick the contract:

1. **Extend the tool surface.** Add `install` and `upgrade` to `GOC_VERBS`
   and change `test_ts_verbs_match_engine_subparsers` to assert
   `engine subparsers + ["install", "upgrade"]` (mirroring how `goc --help`
   handles the cli.py-routed pair). Onboarding then flows through the
   registered tool with the bundled engine, and
   `_is_openclaw_plugin_context()` fires as designed. Cost: the parity test
   loses its "exactly the engine parser" simplicity and gains an
   adjudicated-extras list.
2. **Keep the tool lifecycle-only; fix the skills.** Treat install/upgrade
   as out of scope for the tool (matching its "card lifecycle work"
   description) and rewrite the kickoff/openclaw-kickoff templates (or their
   porter output) to give OpenClaw an explicit working recipe, e.g. an
   `exec` of `PYTHONPATH=<plugin-root> python3 -m goc.cli install ...`.
   Cost: the recipe hard-codes the handler's invocation detail into skill
   prose and needs the plugin root discoverable from the skill context.

Option 1 is the smaller diff and matches user expectation ("the `goc` tool
runs goc verbs"); option 2 keeps the tool schema conservative. Either way the
falsifiable end-state is the same: the shipped onboarding instructions are
executable on a plugin-only OpenClaw host.

## Empirical evidence

`reproduce.py` (regex-extracts `GOC_VERBS` from `openclaw-plugin/index.ts`,
checks for install/upgrade, and counts `goc install` instructions in the
ported kickoff skills):

```
GOC_VERBS (17): validate, quality-pass, done, attest, status, new, wait, advance, unadvance, repair-edges, move, decide, publish, triage, show, migrate, migrate-list-style
ported kickoff skills instruct `goc install` at 11 site(s)
missing from GOC_VERBS: ['install', 'upgrade']
FAIL: the shipped onboarding flow is unexpressible through the shipped tool schema.
```
