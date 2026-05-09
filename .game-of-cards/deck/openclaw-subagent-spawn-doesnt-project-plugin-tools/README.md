---
title: openclaw-subagent-spawn-doesnt-project-plugin-tools
summary: "Plugin-registered tools (e.g. `goc` from the GoC OpenClaw plugin) do not appear in subagent toolsets even with the most permissive operator config: `tools.profile: \"full\"` plus an explicit `tools.subagents.tools.alsoAllow: [\"goc\"]`. Runtime inspect (`openclaw plugins inspect game-of-cards --runtime --json`) confirms the plugin is loaded, imported, and the tool is registered (`toolNames: [\"goc\"]`, `tools: [{names: [\"goc\"], optional: false}]`, `diagnostics: []`). Yet a spawned subagent reports `goc tool not available` and only sees built-in tools (exec, read, write, Trello/Odoo/Web/Image, etc.). Either an OpenClaw subagent tool-projection bug, an undocumented additional config layer, or a doc gap. Filed as a follow-up to `openclaw-plugin-release-smoke-blockers-build-and-spawn-api` once that smoke card's plugin-side issues were all confirmed fixed."
status: open
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: session
advances:
  - provide-openclaw-plugin-for-skills-and-hooks
  - publish-openclaw-plugin
advanced_by:
  - openclaw-plugin-release-smoke-blockers-build-and-spawn-api
tags: [bug, infra]
definition_of_done: |
  - [ ] Reproduce on a clean OpenClaw install with documented config (`tools.profile: "full"`, `tools.subagents.tools.alsoAllow: ["goc"]`, `plugins.entries.game-of-cards.hooks.allowConversationAccess: true`); capture exact OpenClaw version (`openclaw --version`) and Node version
  - [ ] Determine the failure layer: (a) doc gap (additional config knob not yet documented), (b) operator-config issue (something else in the test setup overriding `alsoAllow`), or (c) OpenClaw subagent-toolset-projection bug
  - [ ] If (a): document the missing knob in this card and update `add-openclaw-install-section-to-llms-txt`'s scope (or file a follow-up doc card) so future operators don't hit the same wall
  - [ ] If (b): identify the conflicting config and document the resolution
  - [ ] If (c): file an issue upstream at OpenClaw's tracker; reference this card and the smoke card; capture the issue URL here
  - [ ] Smoke retest with whatever fix lands: subagent invocation in a clean session sees and successfully calls `goc` (e.g., a `goc show <title>` or `goc validate` returns the expected output)
  - [ ] `uv run goc validate` passes
worker:
---

# OpenClaw subagent spawn doesn't project plugin tools

## Background

Filed 2026-05-09 as the residue of `openclaw-plugin-release-smoke-blockers-build-and-spawn-api` once that card's plugin-side fixes (build pipeline, sanctioned subprocess API, esbuild bundle, conversation-hook docs, etc.) were all confirmed working. The plugin registers correctly; the runtime registry has the tool; but the spawn-subagent path doesn't expose it.

## What's verified

After all plugin-side fixes landed (smoke card retests #1–#5, ending with commit `c390722`), the tester applied the documented operator config:

```json5
{
  "tools": {
    "profile": "full",
    "subagents": {
      "tools": {
        "alsoAllow": ["goc"]
      }
    }
  },
  "plugins": {
    "entries": {
      "game-of-cards": {
        "hooks": {
          "allowConversationAccess": true
        }
      }
    }
  }
}
```

`openclaw plugins inspect game-of-cards --runtime --json` reports:

```
status: loaded
imported: True
toolNames: ["goc"]
tools: [{"names": ["goc"], "optional": false}]
diagnostics: []
```

Subagent invocation (the smoke card's DoD item 5(d)) still fails with:

```
goc tool not available
```

The subagent's toolset contains only the standard built-in tools (exec, read, write, Trello, Odoo, web fetch / web search, image generation, etc.) — no plugin tools at all.

## Hypotheses

Three plausible failure layers, in decreasing order of "we can fix it":

### (a) Doc gap — additional knob we haven't found

OpenClaw's `node_modules/openclaw/docs/tools/subagents.md` says:

> With no restrictive `tools.profile`, sub-agents get **all tools except session tools** and system tools.

Plus on `tools.subagents.tools.alsoAllow`:

> Final allow-only filter. It can narrow the already-resolved tool set, but it cannot **add back** a tool removed by `tools.profile`.

We're using `tools.profile: "full"` (which the docs say includes "all core and optional plugin tools") AND `subagents.tools.alsoAllow: ["goc"]` as a belt-and-suspenders. Either the `full` profile actually omits something we don't know about, or `alsoAllow` doesn't reach the subagent layer in the documented way.

### (b) Operator-config conflict — something else is overriding

The tester's config could have a per-agent override (`agents.list[].tools.profile` / `agents.list[].tools.deny`) or a higher-priority filter that wins against the global `tools.profile: "full"`. OpenClaw's tool-policy pipeline (`node_modules/openclaw/dist/effective-tool-policy-DQTaoezb.js`) layers many filters: profile → also-allow → group → owner-only → sandbox → subagent. A conflicting filter at any layer could mask plugin tools.

Diagnostic: the tester could share the full effective config for the agent that's spawning the subagent, plus the subagent's own config if any.

### (c) OpenClaw subagent-toolset-projection bug

The runtime registry has the tool. The policy says it should pass through. Yet the subagent doesn't see it. If (a) and (b) are ruled out, this is an upstream bug — the projection from registered-tool-set → subagent-spawn-toolset doesn't include plugin tools (perhaps only includes built-in tools that go through a different code path).

A repro this would file directly upstream at <https://github.com/openclaw/openclaw> (or the relevant OpenClaw issue tracker — confirm at file time since the org/repo may have moved).

## Cross-references

- `openclaw-plugin-release-smoke-blockers-build-and-spawn-api` — the smoke card; closed once this card was filed. All plugin-side fixes (build, bundle, register, runtime inspect) are validated there. This card carries the residue.
- `provide-openclaw-plugin-for-skills-and-hooks` (active, gate=session) — parent epic; adopting the OpenClaw plugin distribution path. Cannot be closed while this card blocks subagent acceptance.
- `publish-openclaw-plugin` (open, gate=session) — distribution-only follow-up; needs subagent acceptance verified before publish makes sense to broad audience.
- `add-openclaw-install-section-to-llms-txt` (done) — added install docs, but didn't document subagent tool exposure (out of scope for that card).

## Out of scope

- Plugin-side changes. The plugin code is verified correct via `inspect --runtime --json`. Touching `register()` / `api.registerTool()` further is unlikely to fix a downstream projection issue.
- Workarounds that change the plugin's tool name, `optional` flag, or registration shape. Those would only mask the underlying issue without resolving it for any other plugin.

## Notes

- The tester's reproduction environment is `/tmp/goc-release-smoke/` with the OpenClaw runtime installed. They've been running retests #1–#5 of the smoke card on that setup; the same setup applies here.
- If this turns out to be (c), an upstream issue is still useful to file even if we can't fix it ourselves — it documents the gap for other plugin authors and gives OpenClaw maintainers a concrete repro.
