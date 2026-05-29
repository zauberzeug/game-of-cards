---
title: openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs
summary: "The OpenClaw plugin exposes `goc` as a registered tool whose `verb` parameter is constrained to a typebox literal-union built from `GOC_VERBS` (`openclaw-plugin/index.ts:46-61`). That list enumerates 14 verbs but omits `wait` and `repair-edges`, both of which exist in `goc/engine.py` (added at lines 2649 and 2687). OpenClaw subagents calling the tool with `verb: \"wait\"` or `verb: \"repair-edges\"` are rejected at input validation — so the entire stored-impediment-overlay axis of the documented three-axis stuck model, and the half-edge repair flow, are unreachable from the OpenClaw integration."
status: open
stage: null
contribution: medium
created: "2026-05-29T16:04:37Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, meta-fix, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits non-zero on a clean checkout (the assertion that `GOC_VERBS` contains every engine subparser fails because `wait` and `repair-edges` are missing) and exits zero after the fix.
  - [ ] MECHANICAL: `openclaw-plugin/index.ts:46-61` `GOC_VERBS` lists every verb registered by `_build_parser` in `goc/engine.py`, in the same order as the argparse `subparsers.add_parser(...)` calls (current source-of-truth ordering: `validate`, `quality-pass`, `done`, `attest`, `status`, `new`, `wait`, `advance`, `unadvance`, `repair-edges`, `move`, `decide`, `triage`, `show`, `migrate`, `migrate-list-style`).
  - [ ] MECHANICAL: `openclaw-plugin/dist/index.js` regenerated via `npm run build` (or whatever the plugin's documented build command is) so the compiled `GOC_VERBS` array shipped to consumers matches the TS source.
  - [ ] PROCESS: closure log records whether a drift-guard test was added (a small unit test that parses the engine's `subparsers` and asserts equality with the TS literal-union) or explicitly deferred to a follow-up — silent re-drift is what made this defect possible.
---

# OpenClaw plugin `goc` tool cannot call the `wait` or `repair-edges` verbs

## Location

- `openclaw-plugin/index.ts:46-61` — `GOC_VERBS` array (the literal-union
  source).
- `openclaw-plugin/index.ts:63-99` — `GocToolParams` typebox uses
  `Type.Union(GOC_VERBS.map((v) => Type.Literal(v)), ...)`, so the verb
  whitelist is enforced at input validation time.
- `openclaw-plugin/dist/index.js:2386-2400` — the compiled array shipped
  to OpenClaw consumers; identical to the TS source.
- `goc/engine.py:2649` — `subparsers.add_parser("wait", ...)`.
- `goc/engine.py:2687` — `subparsers.add_parser("repair-edges", ...)`.

## What's broken

The OpenClaw plugin's `goc` tool defines its allowed verbs as a typed
literal-union:

```typescript
// openclaw-plugin/index.ts:46-61
const GOC_VERBS = [
  "validate",
  "quality-pass",
  "done",
  "attest",
  "status",
  "new",
  "advance",
  "unadvance",
  "move",
  "decide",
  "triage",
  "show",
  "migrate",
  "migrate-list-style",
] as const;
```

The comment three lines above (`openclaw-plugin/index.ts:44-45`) makes
the contract explicit:

> Mirrors the click subparser surface in goc/cli.py — keep in sync if
> new verbs land. The argparse `commands` field is the source of truth.

It hasn't been kept in sync. `_build_parser` in `goc/engine.py` registers
16 subparsers; the verb list above ships 14. Missing:

- `wait` (`goc/engine.py:2649`) — sets or clears the stored impediment
  overlay (`waiting_on` reason + optional `waiting_until` date). This is
  the third axis of the three-axis stuck model that AGENTS.md
  ("Three-axis 'stuck' model") and `Skill(advance-card)` both call out
  as the documented way to express "blocked by X".
- `repair-edges` (`goc/engine.py:2687`) — previews and applies fixes for
  asymmetric `advances` ↔ `advanced_by` half-edges. The fallback when
  `goc validate` reports a half-edge.

A consumer that tries to use either verb through the OpenClaw plugin
tool is rejected before the tool body runs, because the typebox literal
union refuses any string outside the 14 listed.

## Empirical evidence

`reproduce.py` extracts the `GOC_VERBS` array from the shipped
`openclaw-plugin/dist/index.js`, walks the argparse subparsers in
`goc/engine.py`, and reports the diff:

```
$ uv run python .game-of-cards/deck/openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs/reproduce.py
engine subparsers: validate, quality-pass, done, attest, status, new, wait, advance, unadvance, repair-edges, move, decide, triage, show, migrate, migrate-list-style
GOC_VERBS:         validate, quality-pass, done, attest, status, new, advance, unadvance, move, decide, triage, show, migrate, migrate-list-style
missing from GOC_VERBS: ['wait', 'repair-edges']
FAIL: 2 verbs registered in goc/engine.py are not callable through the OpenClaw plugin tool
```

## Why it matters

Reachability path: an OpenClaw user installs the GoC plugin, follows
the same skill bodies the Claude plugin ships (the OpenClaw plugin's
own `skills/` are ported from `goc/templates/skills/`), and at some
point one of those skills instructs the agent to invoke `goc wait
<title> --reason external` (the canonical instruction in
`Skill(advance-card)` Step 6 and in `Skill(card-schema)` "Three-axis
stuck model"). The agent constructs `{verb: "wait", args: [...]}` for
the `goc` tool. OpenClaw's typebox input validation rejects the call
before reaching `runGoc`, returning a schema error to the agent. The
agent cannot complete the instruction — and because the rejection is a
validation error rather than a runtime missing-command error, the
agent's typical "retry by shelling out via Bash" fallback also fails
(the Claude PATH-prepend trick is documented as absent on OpenClaw
in `openclaw-plugin/index.ts:16-26`; `goc` is *only* reachable via the
registered tool).

Concrete consequences:

- The stored-impediment-overlay axis of the three-axis model is
  unreachable. `Skill(advance-card)` Step 6 ("set or clear the
  impediment overlay with `goc wait`") cannot be performed by an
  OpenClaw subagent. The two adjacent axes (progress status,
  derived dependency-readiness) remain reachable, so the user is left
  with a deceptive partial integration.
- Half-edge repair is unreachable. A deck that ends up with a half-edge
  (e.g. from a partial commit, an external editor, or a merge conflict
  resolved in one card and not the other) cannot be fixed from
  OpenClaw via the canonical mechanism. `goc validate` flags the
  half-edge but the listed remediation (`goc repair-edges --apply`)
  bounces off the schema.
- The drift mode is silent: `npm run build` regenerates `dist/index.js`
  from the same out-of-date TS source, so the next release ships the
  same gap. There is no parity check between the TS `GOC_VERBS` and the
  engine's argparse subparsers — neither `tests/`'s plugin-parity
  suite nor `scripts/sync_plugin_assets.py` covers it. The
  `port_skills_to_openclaw.py` drift guard catches *skill* drift, not
  *tool-surface* drift.

## Fix

Two-step mechanical fix; no design choice.

1. Edit `openclaw-plugin/index.ts:46-61` and add `"wait"` and
   `"repair-edges"` in the same positions they appear in the engine's
   `_build_parser` (between `new` and `advance`, and between `unadvance`
   and `move`, respectively — `goc/engine.py:2649` and `:2687`).
2. Run the plugin's documented build (`npm run build` in
   `openclaw-plugin/`) so `dist/index.js` is regenerated. The
   compiled `GOC_VERBS` array shipped at `openclaw-plugin/dist/index.js:2386`
   must update accordingly.

Recommended (DoD's PROCESS item): add a small drift guard in
`tests/test_plugin_mirror_parity.py` (or a sibling test) that imports
`goc.engine`, walks the argparse subparsers, parses the `GOC_VERBS`
array out of `openclaw-plugin/index.ts`, and asserts equality. The
existing parity test infrastructure (e.g.
`scripts/port_skills_to_openclaw.py --check`) already shows how to fail
the build on drift; this would extend the same discipline to the tool
surface, which is currently uncovered.
