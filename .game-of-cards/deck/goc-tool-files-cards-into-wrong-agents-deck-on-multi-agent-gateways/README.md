---
title: goc-tool-files-cards-into-wrong-agents-deck-on-multi-agent-gateways
summary: The goc tool's cwd fallback uses one global sessionProjectDir, so on multi-agent gateways cards land in whichever agent's session started last.
status: open
stage: null
contribution: medium
created: "2026-06-12T03:44:12Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] Reproduce on a two-agent gateway: agent A session_start, then agent B goc call without cwd lands in A's deck
  - [ ] Fix: cwd resolution is per calling session/agent, never another session's value
  - [ ] Regression test covering the multi-agent case
  - [ ] Released to ClawHub; fclaw updated and AGENTS.md workaround note relaxed
---

# goc tool files cards into the wrong agent's deck on multi-agent gateways

## Trigger

fclaw goc rollout 2026-06-12: enabling the `goc` tool for the four sandboxed
family agents (anco/hobbes/jinx/lasse) on the consolidated multi-agent
gateway exposed a cross-agent routing flaw in the plugin's cwd handling.

## Evidence (openclaw-plugin v0.0.23, dist/index.js)

```js
let sessionProjectDir;            // module-global, ONE slot per gateway process
api.on("session_start", async (ctx) => {
  const projectDir = ctx?.projectDir ?? process.cwd();
  sessionProjectDir = projectDir; // every session of EVERY agent overwrites it
});
// tool execute():
const requestedCwd = params.cwd ?? sessionProjectDir ?? process.cwd();
// fallback when requestedCwd does not exist on host:
for (const candidate of [sessionProjectDir, process.cwd()]) { ... }
```

## Impact

On a single-agent install (zoe) `sessionProjectDir` is always the same
workspace, so the bug is invisible. On a multi-agent gateway (fclaw: 5
agents, one workspace each) a `goc` tool call WITHOUT an explicit `cwd` —
or with a sandbox-path `cwd` like `/workspace` that does not exist on the
host — resolves to the project dir of the MOST RECENTLY STARTED session of
ANY agent. Cards are then filed into another family member's deck:
cross-user data mixing.

## Suggested fix

Replace the global with a per-session (or per-agent) map keyed from the
session context (capture in `session_start`, look up in `execute` via the
calling session's ctx; the SDK context shapes are already flagged
TODO(verify-context-shape) in index.ts). Fall back to the calling agent's
configured workspace, never to another session's value.

## Workaround deployed on fclaw (2026-06-12)

- In-sandbox shell `goc` baked into `openclaw-sandbox-fclaw` image
  (vendored package, operates on `/workspace` = always the agent's own deck).
- AGENTS.md per agent: when using the first-class tool, ALWAYS pass
  `cwd: /var/lib/openclaw/workspace-<id>`.

