---
title: openclaw-plugin-cannot-show-the-deck-queue-through-tool-or-exec
summary: "On OpenClaw the deck's primary read — the bare queue, --board, --ready, --json — is unreachable by both routes the plugin's own ported skills name. The registered goc tool requires a verb and buildArgs always injects it, so the engine's no-subcommand renderer can never run; and the porter's fallback instruction to shell out via exec targets a bare goc binary the OpenClaw payload deliberately does not ship. Every goc bullet in the ported Context blocks is a no-subcommand invocation, so none of them is executable on a stock OpenClaw host."
status: open
stage: null
contribution: high
created: "2026-07-27T01:11:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the `## Decision required` below is resolved — pick which surface carries no-subcommand reads (tool-side `queue` verb, optional `verb`, or a porter-emitted `python3 -m goc.cli` recipe).
  - [ ] TDD: `reproduce.py` exits zero (a no-subcommand `goc` read is reachable on a stock OpenClaw host), having exited 1 before the fix.
  - [ ] TDD: a regression test pins the chosen surface, so a later `GOC_VERBS` / porter edit cannot silently remove it again — the same drift that `tests/test_plugin_mirror_parity.py` already guards for engine subparsers.
  - [ ] MECHANICAL: `scripts/port_skills_to_openclaw.py`'s `transform_context_block` no longer instructs `exec` of a bare `goc`, and `scripts/port_skills_to_openclaw.py --check` is green after re-porting the affected skills.
  - [ ] MECHANICAL: if the fix touches `openclaw-plugin/index.ts`, `openclaw-plugin/dist/index.js` is rebuilt (`npm run build`) so the shipped bundle matches.
  - [ ] MECHANICAL: `uv run goc validate` passes.
---

# The OpenClaw plugin cannot show the deck queue through either route its skills name

## Location

- `openclaw-plugin/index.ts:77-86` — `GocToolParams.verb` is a required
  literal union (`Type.Union`, **not** wrapped in `Type.Optional`).
- `openclaw-plugin/index.ts:129` — `buildArgs` returns
  `[...flagTokens, input.verb, ...(input.args ?? [])]`; the verb is spliced
  unconditionally.
- `openclaw-plugin/dist/index.js:2406-2449` — the compiled artifact consumers
  actually load; identical on both points.
- `goc/engine.py:4049-4050` — `if args.command is None: _cmd_default(args)`.
  The queue table, `--board`, `--ready`, `--json` and the leverage line all
  live behind that branch.
- `scripts/port_skills_to_openclaw.py:106-107` — the porter's injected
  fallback text: *"For bare-queue listings with no subcommand, shell out via
  the `exec` tool:"*.
- `openclaw-plugin/package.json` — no `bin` field, no `bin/` entry in
  `files:`; there is no `openclaw-plugin/bin/` directory (unlike
  `claude-plugin/bin/goc` and `codex-plugin/bin/goc`).

## What's broken

The engine renders the deck only when argparse resolves **no subcommand**:

```python
# goc/engine.py:4049
    if args.command is None:
        _cmd_default(args)
```

`_cmd_default` is the whole read surface — the value-sorted queue, the
kanban board, `--ready`, `--json`, the active-card banner, the leverage
line. Every named verb is a different branch that ignores the top-level
filter flags. Verified against the engine in this repo:

```
$ goc --board triage        # the only shape the tool can emit
No parked cards (gate ≠ none).      # ← triage ran; --board was ignored
```

**Route 1 — the registered tool — cannot emit that shape.** The `verb`
parameter is a required literal union, and `buildArgs` always splices it:

```ts
// openclaw-plugin/index.ts:119-130
function buildArgs(input: GocToolInput): string[] {
  const flagTokens: string[] = [];
  ...
  if (f.board) flagTokens.push("--board");
  if (f.json) flagTokens.push("--json");
  ...
  return [...flagTokens, input.verb, ...(input.args ?? [])];
}
```

So `{flags: {board: true}, verb: "show"}` runs `goc --board show` — `show`,
not the board. The tool's own `flags` description states the opposite:

> "Top-level filter flags applied before the verb. **Use these for
> bare-queue listings**; otherwise prefer verb-specific flags via `args`."

Those flags only have an effect on the one invocation shape the tool cannot
produce.

**Route 2 — `exec` — has no binary to run.** The porter injects this
paragraph into every ported skill whose source has a `## Context` block:

```python
# scripts/port_skills_to_openclaw.py:102-108
        "Before running the body of this skill, the agent should see current "
        "deck state. Run these via the `goc` tool (top-level filters like "
        "`--status` / `--tag` / `--worker` map to the tool's `flags` "
        "parameter; the subcommand maps to `verb`). For bare-queue listings "
        "with no subcommand, shell out via the `exec` tool:\n\n"
```

But the OpenClaw payload deliberately ships no `goc` executable, and the
plugin's own documentation says so three times:

- `openclaw-plugin/index.ts:16-19` — "OpenClaw has no auto-PATH-prepend
  mechanism for plugin binaries (verified via the PATH-integration spike…).
  So the plugin exposes goc as a registered tool rather than a shell binary
  on PATH."
- `openclaw-plugin/README.md:66-68` — "`python3` (3.10+) on PATH. The plugin
  invokes the bundled engine via `python3 -m goc.cli` from the tool handler —
  no `uv`, no `pipx`, no separate `pipx install game-of-cards` step."
- `goc.md:214` — "**`goc` as a registered OpenClaw tool** — not a shell
  binary on PATH."

`exec("goc --ready")` on a stock host is therefore command-not-found. The
only working shell form is `PYTHONPATH=<plugin-root> python3 -m goc.cli
--ready`, and the plugin root is exactly the host-side path a sandboxed
session cannot resolve — the failed-read-and-guess loop that the tool-only
`skill` verb was added to eliminate
([openclaw-plugin-skills-force-repeated-reads-every-session](../openclaw-plugin-skills-force-repeated-reads-every-session/)).

## Empirical evidence

`reproduce.py` reads the shipped bundle, the porter, and the ported skills:

```
$ uv run python .game-of-cards/deck/openclaw-plugin-cannot-show-the-deck-queue-through-tool-or-exec/reproduce.py
tool verb union (18): validate, quality-pass, done, attest, status, new, wait, advance, unadvance, repair-edges, move, decide, publish, triage, show, migrate, migrate-list-style, skill
verb declared Type.Optional: False
buildArgs unconditionally splices input.verb: True
engine gates _cmd_default on `args.command is None`: True
payload ships a goc binary: bin field=False bin/ dir=False
index.ts states OpenClaw has no auto-PATH-prepend: True
README disclaims the pipx prerequisite: True
porter emits the `exec` fallback instruction: True
ported Context `goc` bullets: audit-deck=4, next-card=2, retrospective=1, standup=3 (total 10)
  expressible through the tool (carry a subcommand): 0/10

FAIL: the registered `goc` tool cannot emit a no-subcommand argv (verb is required and buildArgs always splices it), so the engine's `args.command is None` renderer — queue / --board / --ready / --json — is unreachable through the tool
FAIL: the porter instructs agents to `exec` a bare `goc …` while the OpenClaw payload ships no `goc` binary (no bin/, no bin field) and documents no PATH-prepend — the fallback is command-not-found on a stock host
FAIL: all 10 `goc` bullets the porter emits across 4 ported skills are no-subcommand invocations, so none is expressible through the tool the same paragraph points at
```

**0 of 10.** The paragraph splits its own bullets into "run via the tool" and
"shell out for the bare ones", but every bullet it lists falls on the second
side — and the second side does not exist.

## Why it matters

Reachability: fresh OpenClaw host → `openclaw skills install game-of-cards`
→ user says "what's next" → the `next-card` skill loads → its first
instruction is to read `goc --status active -v` and `goc --ready -v`. The
agent has two documented options and both fail: the tool rejects a verbless
call at input validation, and `exec goc` is command-not-found. The same
happens on the first step of `pull-card`, `audit-deck`, `standup`,
`retrospective`, and `scan-deck` — every read-first skill in the payload.

The write surface is fine (`new`, `status`, `done`, `decide` all carry
subcommands), so the failure mode is asymmetric and quiet: an OpenClaw agent
can *file and close* cards but cannot *see the deck*, which is precisely the
"deck is the queue" premise the methodology rests on.

This is the third instance of one shape — the tool's `verb` union deciding
what is reachable on OpenClaw:

- [openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs](../openclaw-plugin-goc-tool-cannot-call-wait-or-repair-edges-verbs/)
  (closed) — two engine subparsers missing from the union; fixed by pinning
  `GOC_VERBS` to `_build_parser`'s subparsers.
- [openclaw-plugin-goc-tool-cannot-call-install-or-upgrade-verbs](../openclaw-plugin-goc-tool-cannot-call-install-or-upgrade-verbs/)
  (open) — the two `cli.py`-routed verbs, which that same pinning
  structurally excludes.
- This card — the invocation that is *not a verb at all*, which no amount of
  subparser pinning can reach.

The pinning contract fixed instance 1 and, by construction, created
instances 2 and 3: `tests/test_plugin_mirror_parity.py` asserts `GOC_VERBS`
equals the engine's subparser list exactly, so the union can only ever
describe subcommands. If a fourth instance lands, the family should become
one architectural card about how the OpenClaw tool models the CLI surface
rather than a fourth point fix.

## Decision required

Which surface carries no-subcommand reads on OpenClaw? Three credible paths,
and the choice changes what gets tested and re-ported.

**A. Add a tool-only verb (e.g. `queue`) to `TOOL_ONLY_VERBS`.**
`execute` maps it to an empty subcommand slot so `buildArgs` emits
`[...flagTokens]` with no verb. Keeps the parity contract intact (`skill`
already established the tool-only escape hatch at
`openclaw-plugin/index.ts:68-75`), and the verb list stays self-documenting
in the tool schema the agent sees. Costs an `index.ts` change plus an
`npm run build` to refresh `dist/index.js`. Needs a name the agent will
guess — `queue` reads well next to `--board` / `--ready`, but it is not a
real CLI verb, so the tool description must say so.

**B. Make `verb` optional.** Smallest schema delta; `buildArgs` skips the
splice when `verb` is undefined. But it weakens the parameter that currently
carries all the "what can I do" affordance, and an omitted-required-field
call is a shape agents produce by accident, so silent bare-queue runs would
replace today's loud validation error.

**C. Leave the tool alone; fix the porter text.** Replace the `exec goc …`
instruction with the working shell form (`python3 -m goc.cli` with
`PYTHONPATH` set to the plugin root) or with a tool-call recipe. Zero plugin
changes, but it hands the agent back the host-path-resolution problem the
`skill` verb exists to avoid, and it leaves the tool's own `flags`
description ("Use these for bare-queue listings") factually wrong.

Note that **the porter text needs an edit under all three options** — under
A and B it should point at the new tool shape instead of `exec`. The
decision is only about which surface it points *at*.

## Fix

Determined by the decision above. Under any option, also correct the
`flags` parameter description at `openclaw-plugin/index.ts:104-106`, which
today tells the agent to use those flags for the one invocation shape the
tool cannot emit.
