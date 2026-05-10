---
title: openclaw-subagent-plugin-tools-alsoallow-ignored
summary: "OpenClaw 2026.5.6 ignores `tools.subagents.tools.alsoAllow` while building plugin tool allowlists for subagents. The GoC plugin registers `goc` correctly and main sessions can call it, but spawned subagents still cannot see the `goc` first-class tool. This matches upstream issue openclaw/openclaw#23359 and open PR #51388."
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
  - [ ] Track upstream OpenClaw issue/PR state: issue #23359 and PR #51388, or their successor if superseded
  - [ ] Document the exact affected OpenClaw version observed locally (`openclaw --version`)
  - [ ] Add/update GoC OpenClaw install notes with the current limitation and safe workaround guidance
  - [ ] Once an OpenClaw release contains the fix, retest: main session sees `goc`, spawned subagent sees `goc`, and subagent can run `goc validate`
  - [ ] Remove or revise workaround notes after the fixed OpenClaw version is the minimum supported version
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# OpenClaw subagent plugin tools `alsoAllow` ignored

## Problem

The Game of Cards OpenClaw plugin is registering its `goc` tool correctly, but the tool is not projected into spawned subagents when enabled through `alsoAllow`.

Observed locally on 2026-05-10:

- OpenClaw version: `2026.5.6 (c97b9f7)`
- Plugin install path: `~/.openclaw/extensions/game-of-cards/`
- Main OpenClaw config includes:

```json5
{
  "tools": {
    "profile": "coding",
    "alsoAllow": ["goc"]
  },
  "plugins": {
    "entries": {
      "game-of-cards": {
        "enabled": true,
        "hooks": {
          "allowConversationAccess": true
        }
      }
    }
  }
}
```

Runtime inspection shows the plugin side is healthy:

```text
openclaw plugins inspect game-of-cards --runtime --json
status loaded
imported True
toolNames ["goc"]
tools [{"names": ["goc"], "optional": false}]
diagnostics None
```

Main-session call works:

```text
goc validate returned exit 0
```

But an isolated spawned subagent still reports:

```text
`goc` is not available as a first-class tool
```

## Online finding

This matches known upstream OpenClaw behavior:

- Issue: <https://github.com/openclaw/openclaw/issues/23359>
  - `tools.subagents.tools.alsoAllow is accepted by schema but ignored at runtime`
- PR: <https://github.com/openclaw/openclaw/pull/51388>
  - `fix(tool-policy): include alsoAllow entries in plugin tool allowlist …`
  - Status observed 2026-05-10: open

Root cause described upstream: plugin tool allowlist collection reads `policy.allow` but does not include `policy.alsoAllow`. Therefore plugin tools can be registered and visible in the runtime registry, while still failing to appear in subagent sessions.

## Current assessment

This is not a Game of Cards plugin registration bug. The plugin's manifest, runtime import, and `api.registerTool()` path work. The failure is downstream in OpenClaw's subagent/plugin-tool policy projection.

## Workaround notes

Be careful with `tools.subagents.tools.allow`: it is a final allow-only filter and may accidentally remove standard subagent tools. Prefer documenting the limitation until OpenClaw includes the upstream fix, unless a very narrow smoke environment needs a temporary workaround.

## Retest recipe

After OpenClaw includes the fix:

1. Ensure config grants `goc` for the relevant profile/subagent path.
2. Restart/refresh OpenClaw.
3. Verify main session:

```text
goc validate
```

4. Spawn a clean subagent and ask it to call first-class `goc validate` without shell fallback.
5. Close this card when both calls succeed and docs/workarounds are updated.
