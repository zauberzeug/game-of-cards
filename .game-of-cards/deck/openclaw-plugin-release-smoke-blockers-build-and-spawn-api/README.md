---
title: openclaw-plugin-release-smoke-blockers-build-and-spawn-api
summary: "Two release-blocking defects surfaced by a 2026-05-09 PM tester smoke run on the OpenClaw plugin: (a) plugin ships only `index.ts`, not compiled `dist/index.js`, so the runtime never executes `register(api)` and the `goc` tool never registers (visible as `contracts.tools: ['goc']` but `toolNames: []` in `openclaw plugins inspect`); (b) plugin imports `node:child_process` for `spawn`, which OpenClaw's safe-install policy blocks (currently only installs with `--dangerously-force-unsafe-install`). Replace with `api.runtime.system.runCommandWithTimeout` (the sanctioned subprocess API per docs)."
status: done
stage: null
contribution: high
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances:
  - provide-openclaw-plugin-for-skills-and-hooks
  - openclaw-subagent-spawn-doesnt-project-plugin-tools
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `openclaw-plugin/tsconfig.json` emits compiled output (`noEmit: false`, `outDir: "./dist"`); `openclaw-plugin/dist/index.js` exists and matches `index.ts`
  - [x] `openclaw-plugin/package.json` declares `main: "./dist/index.js"`, `openclaw.extensions: ["./dist/index.js"]`, and scripts: `build`, `prepare` (auto-build after npm install), `prepublishOnly` (auto-build before npm publish)
  - [x] `openclaw-plugin/index.ts` no longer imports from `node:child_process`; subprocess invocations use `api.runtime.system.runCommandWithTimeout(cmd, args, opts)` per <https://docs.openclaw.ai/plugins/sdk-runtime.md>. `runGoc` helper is moved inside `register(api)` so it can capture `api.runtime` in its closure.
  - [x] Build artifact: `cd openclaw-plugin && npm install && npm run build` produces a `dist/index.js` that's committed to the repo.
  - [x] Smoke retest by the original tester confirms: (a) `openclaw plugins install <local-path>` no longer fails for missing JS — ✅; (b) install no longer requires `--dangerously-force-unsafe-install` — ✅; (c) `openclaw plugins inspect game-of-cards --runtime --json` shows `imported: True`, `toolNames: ["goc"]`, `tools: [{names: ["goc"], ...}]` — ✅ (note: default `inspect --json` is the static-snapshot view; `--runtime` is required to see the runtime registry); (d) a subagent invocation can see and call the `goc` tool — delegated to follow-up `openclaw-subagent-spawn-doesnt-project-plugin-tools` after the tester verified that even the most-permissive operator config (`tools.profile: "full"` + `subagents.tools.alsoAllow: ["goc"]` + `allowConversationAccess: true`) doesn't surface plugin tools in subagents. Plugin code is verified correct via `inspect --runtime --json`; the projection layer is upstream of this card's scope.
  - [x] `uv run goc validate` passes.
  - [x] Side finding (out of this card's scope): website / `llms.txt` still recommends `uv tool install` as the install path. Reviewer (2026-05-09) decided the scope expansion is large enough to warrant a separate card rather than stretching `llms-txt-still-recommends-uv-tool-install-as-preferred`'s narrow uv→pipx fix. Resolved by filing `add-openclaw-install-section-to-llms-txt`.
worker: {who: "claude[bot]", where: main}
---

# OpenClaw plugin release-smoke blockers — build pipeline + sanctioned spawn API

## Action required (gate still session as of retest #5)

Implementation history (compressed):
- `7cb062c` (α) — compiled JS + sanctioned spawn API.
- Retest #2 → `7fe3d66` — rephrase comments so safe-install scanner stops tripping on `child_process` substring; DoD item 7 (llms.txt scope) ticked, follow-up `add-openclaw-install-section-to-llms-txt` filed.
- Retest #3 → `98146e7` — declared `@sinclair/typebox` as runtime dep. **Insufficient** because `openclaw plugins install <local-path>` copies the tree without running `npm install`.
- Retest #4 → `a352f09` — bundled with esbuild; `dist/index.js` is now self-contained (104 kB) with typebox inlined and only `openclaw/plugin-sdk/*` + Node builtins external (the former resolves via OpenClaw's jiti alias map per `node_modules/openclaw/dist/sdk-alias-DiiCKlea.js`).
- Retest #5 — debug instrumentation (since removed) confirmed `register(api)` runs to completion and `api.registerTool({name: "goc"})` returns. **Plugin code is correct.**
- **Diagnostic: default `inspect --json` is the static-snapshot view** — it does not show runtime registrations. `openclaw plugins inspect game-of-cards --runtime --json` shows `imported: True`, `toolNames: ["goc"]`, `tools: [{names: ["goc"], optional: false}]`. The "phantom" tools=[]/imported=false readings of retests #2–#5 were a false-negative caused by reading the wrong inspect view.

**Remaining: subagent tool exposure (DoD item 5d).** Tester reports the runtime registry has the tool but a subagent invocation says "goc tool not available". This is OpenClaw's tool-policy / agent-harness layer, not the plugin's `register()`. Per `node_modules/openclaw/docs/tools/subagents.md`:

> With no restrictive `tools.profile`, sub-agents get **all tools except session tools** and system tools.

So if the operator's config sets a `tools.profile` (e.g., `coding`), plugin tools are filtered out. The fix is operator-side; see "Subagent tool exposure" below.

## Subagent tool exposure (operator config)

`goc` is registered as a required tool (`api.registerTool({name: "goc", ...})` — single-arg form, `optional: false`). The runtime registry contains it (verified by `inspect --runtime --json`). The remaining gap is OpenClaw's tool-policy filter. Options for the operator (from least to most surgical):

1. **Profile-only with `alsoAllow`** — keep the existing profile; add `goc` to the agent's `tools.alsoAllow`:
   ```json5
   { agents: { defaults: { tools: { alsoAllow: ["goc"] } } } }
   ```
2. **Subagent-specific allow** — narrow the lever further to subagent runs only:
   ```json5
   { tools: { subagents: { tools: { alsoAllow: ["goc"] } } } }
   ```
3. **Drop the restrictive profile** — if the agent's intended scope includes plugin tools generally, set `tools.profile: "full"` (or remove the profile entirely).

The tester's setup will tell us which lever fits; this card does not need to make the choice unilaterally.

## Conversation-hook opt-in (operator config)

`agent_end` is an OpenClaw `CONVERSATION_HOOK_NAMES` entry (`node_modules/openclaw/dist/types-CdFhLeaX.js`). Non-bundled plugins have conversation-hook registrations silently dropped unless the operator opts in:

```json5
{ plugins: { entries: { "game-of-cards": { hooks: { allowConversationAccess: true } } } } }
```

Without this, the GoC pattern-generalization-check hook (`agent_end` consumer) is registered as a no-op. The plugin still works for tool calls and the other two hooks (`session_start`, `before_prompt_build`) — only the post-turn pattern reminder is suppressed.

## Closure path

Once the operator confirms (with `alsoAllow` / profile change in place) that a subagent can see and call `goc`:

```
goc decide openclaw-plugin-release-smoke-blockers-build-and-spawn-api \
  --decision "subagent invocation acceptance verified after operator-side tools.alsoAllow" \
  --because "OpenClaw's default tool policy filters plugin tools out of restrictive profiles; user config knob is documented in this card's body"
goc done openclaw-plugin-release-smoke-blockers-build-and-spawn-api
```

Side-finding (`add-openclaw-install-section-to-llms-txt`) is already closed (`fa5cbb1`). The two operator-config notes above belong in the OpenClaw-section of `site/llms.txt` and the plugin's eventual README — both follow-up cards if not already filed.

## Background

The α implementation of the OpenClaw plugin landed across four commits 2026-05-09 PM (closing 10/13 DoD on the parent `provide-openclaw-plugin-for-skills-and-hooks`). A first release-smoke test exercised the actual install path on an OpenClaw runtime and surfaced two release-blocking defects. This card captures both, plus a side finding for separate triage.

## Tester findings (2026-05-09 PM)

**Working:**

- Plugin loads after a manual patch + install.
- Gateway log shows `game-of-cards` registered.
- Skills are visible/ready in the workspace.

**Release blockers:**

1. ~~`openclaw plugins install game-of-cards` returns "no npm package"~~ — not-a-bug; tracked under `publish-openclaw-plugin` (npm publish step required first).
2. **No compiled JS.** Local install from `openclaw-plugin/` fails because `index.ts` exists but `dist/index.js` does not. OpenClaw's safe install path needs compiled output.
3. **`tsconfig.json` has `noEmit: true`.** Same root cause as (2): TypeScript build emits no runtime JS, so even with proper config, the plugin tree contains no executable entry point.
4. **`child_process` import blocked.** Install requires `--dangerously-force-unsafe-install` because `index.ts` imports `spawn` from `node:child_process`. OpenClaw's plugin sandbox policy blocks raw subprocess access from plugin code; the sanctioned API is `api.runtime.system.runCommandWithTimeout(cmd, args, opts)` (per <https://docs.openclaw.ai/plugins/sdk-runtime.md>).
5. **Tool registration silently fails.** `openclaw plugins inspect game-of-cards --json` shows `contracts.tools: ["goc"]` (declared in `openclaw.plugin.json`) but `toolNames: []` and `tools: []` (runtime didn't actually register). A subagent invocation has no `goc` tool. Root cause: the plugin entry never executes (no compiled JS to run), so `register(api)` never fires, so `api.registerTool({ name: "goc", ... })` never gets called.

Items 2, 3, 5 collapse to one fix: **add a build pipeline.**
Item 4 is a separate fix: **swap to the sanctioned subprocess API.**

**Side finding (out of scope):** website / `llms.txt` still recommends `uv tool install` as the preferred install path. For OpenClaw consumers, the plugin path should lead.

## Fix plan

### Cluster A — build pipeline

1. `tsconfig.json`:
   - Set `noEmit: false`.
   - Set `outDir: "./dist"`.
   - Set `rootDir: "./"` (or equivalent include scoping) so `dist/index.js` lands at `dist/index.js` (not nested).
   - Keep `allowImportingTsExtensions: false` (incompatible with emit).

2. `package.json`:
   - Add `main: "./dist/index.js"`.
   - Update `openclaw.extensions` to `["./dist/index.js"]` (point runtime at compiled output).
   - Add scripts: `build`, `prepare` (auto-build after npm install), `prepublishOnly`.
   - Update `files` to include `dist/`.

3. `dist/` stays tracked in the repo (no `npm install` required to consume from a checkout — tester convenience). A future card can add a build-parity tripwire similar to `validate_plugin_mirror_parity` if dist/-vs-source drift becomes recurring.

4. Run `npm install` + `npm run build` once locally; commit the resulting `dist/index.js` plus `package-lock.json`.

### Cluster B — sanctioned subprocess API

1. Remove `import { spawn } from "node:child_process";` from `index.ts`.

2. Move `runGoc` inside `register(api)` so it can capture `api.runtime` in its closure.

3. Replace `spawn("python3", [...], opts)` with `await api.runtime.system.runCommandWithTimeout("python3", ["-m", "goc.cli", ...args], { cwd, env, timeoutMs: 60000 })`. The full signature isn't documented at <https://docs.openclaw.ai/plugins/sdk-runtime.md>; assume the result has `{ exitCode, stdout, stderr }` (matches the prior shape). Mark with `TODO(verify-shape)` for the smoke retest to confirm.

4. The three lifecycle hooks (`session_start`, `before_prompt_build`, `agent_end`) don't shell out — they only read the local filesystem. They keep their current shape; the only refactor is `runGoc`.

## Validation

- After the changes, `cd openclaw-plugin && npm install && npm run build` should produce `dist/index.js`.
- `uv run goc validate` and `python3 scripts/sync_plugin_assets.py --check` continue to pass.
- The 9 plugin-mirror-parity tests continue to pass.
- The original tester reruns the smoke flow.

## Cross-references

- `provide-openclaw-plugin-for-skills-and-hooks` — parent (advanced by this card)
- `publish-openclaw-plugin` — release-blocker #1 (npm publish, separate card)
- `llms-txt-still-recommends-uv-tool-install-as-preferred` — side finding
- `split-claude-specific-content-out-of-generic-kickoff-skill` — sibling advance edge on the same parent

## Decision

*Resolved 2026-05-09:* Close the card with item 5(d) delegated to follow-up openclaw-subagent-spawn-doesnt-project-plugin-tools.

*Reasoning:* All plugin-side defects (build pipeline, sanctioned spawn API, scanner-comment trip, runtime-dep bundle) are fixed; runtime inspect (--runtime --json) confirms the goc tool is registered. Subagent tool exposure failed even with the most-permissive operator config (tools.profile=full + subagents.tools.alsoAllow=[goc] + allowConversationAccess=true), so the residual is upstream of this card's plugin-side scope. Closing here keeps the smoke umbrella from staying open indefinitely on a non-plugin issue and gives the subagent-projection finding its own briefing.
