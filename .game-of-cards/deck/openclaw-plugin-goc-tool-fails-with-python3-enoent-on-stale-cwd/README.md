---
title: openclaw-plugin-goc-tool-fails-with-python3-enoent-on-stale-cwd
summary: "OpenClaw plugin's goc tool spawns python3 with the agent-supplied cwd. In sandboxed sessions the agent passes a sandbox-internal path such as `/workspace` that does not exist on the host, so Node reports `spawn python3 ENOENT` even though python3 is installed. Validate the requested cwd and fall back to the project directory captured at session_start before spawning."
status: active
stage: null
contribution: medium
created: 2026-05-10
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] Capture `ctx.projectDir` at the `session_start` hook into a closure-scoped variable usable by the tool handler
  - [ ] Tool `execute` validates that the resolved cwd exists; if not, falls back in order: captured session projectDir, then `process.cwd()`
  - [ ] Fallback emits a diagnostic line on the stderr channel returned to the caller naming both the requested cwd and the chosen fallback, so future sandbox-bridge breakage is self-explaining instead of being attributed to a missing python3 binary
  - [ ] `npm run build` in `openclaw-plugin/` succeeds and `dist/index.js` reflects the change
  - [ ] `uv run goc validate` passes
worker: {who: Rodja Trappe, where: main}
---

# OpenClaw plugin goc tool fails with python3 ENOENT on stale cwd

## Problem

In sandboxed agent sessions (the original report came from a Slack-bridged
OpenClaw subagent run), calling the first-class `goc` plugin tool returns:

```
spawn python3 ENOENT
```

Reading the message literally suggests python3 is missing on the host, but
the host has python3 installed and the local CLI fallback works. A
host-side reproduction with `spawnSync('python3', […], { cwd: '/workspace' })`
returns the same ENOENT, confirming that Node's spawn raises ENOENT both
when the binary is missing **and when the cwd does not exist**.

Root cause: the agent runs inside a sandbox whose filesystem maps the
project to `/workspace`, but the OpenClaw plugin runtime (and therefore
this plugin's tool handler) executes host-side. The agent passes its
sandbox-internal cwd through to the tool's `cwd` parameter, the plugin
forwards it unchanged into `api.runtime.system.runCommandWithTimeout(["python3", …], { cwd })`,
and the host has no `/workspace` directory.

## Where the path enters the spawn call

`openclaw-plugin/index.ts`:

- Line 277-278 — `execute` reads `params.cwd ?? process.cwd()` from the
  agent-supplied tool input.
- Line 256-259 — `runGoc` forwards that cwd into
  `runCommandWithTimeout(["python3", "-m", "goc.cli", …], { cwd, … })`
  without checking that it exists on the host.

The `session_start` hook already receives `ctx.projectDir` (line 298-310)
and uses it for active-card discovery, but does not retain it for use
by other handlers in the same plugin instance.

## Fix shape (Option 1)

1. Add a closure-scoped `let sessionProjectDir: string | undefined` inside
   `register()` and assign it from `ctx.projectDir` in the `session_start`
   handler. (Also assign it lazily from `agent_end` / `before_prompt_build`
   contexts when available, so a tool call before the first session_start
   still has a hint.)
2. In the tool's `execute`, after resolving `cwd = params.cwd ?? sessionProjectDir ?? process.cwd()`,
   probe with `fs.access(cwd)`. On failure, fall back to
   `sessionProjectDir ?? process.cwd()` if it differs from the failing path.
3. When the fallback engages, prepend a single diagnostic line to the
   tool's `stderr`-equivalent return text:
   `[goc plugin] requested cwd "<x>" does not exist on host; using "<y>" instead.`
   Future sandbox-bridge breakage will then be self-explaining rather than
   misattributed to python3.

This is intentionally defensive only — it does not try to translate
sandbox paths to host paths (e.g. mapping `/workspace/src` →
`<projectDir>/src`). A nested mismatch still falls back to the project
root, where `goc validate` and the other read-only verbs still work.

## Out of scope

- The `tools.subagents.tools.alsoAllow` projection bug tracked under
  `openclaw-subagent-plugin-tools-alsoallow-ignored`. That card describes
  a different failure mode (the tool is invisible to the subagent), is
  blocked on an upstream OpenClaw release, and is not addressed here.
- Path translation of nested sandbox paths.
