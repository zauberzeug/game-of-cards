---
title: openclaw-plugin-release-smoke-blockers-build-and-spawn-api
summary: "Two release-blocking defects surfaced by a 2026-05-09 PM tester smoke run on the OpenClaw plugin: (a) plugin ships only `index.ts`, not compiled `dist/index.js`, so the runtime never executes `register(api)` and the `goc` tool never registers (visible as `contracts.tools: ['goc']` but `toolNames: []` in `openclaw plugins inspect`); (b) plugin imports `node:child_process` for `spawn`, which OpenClaw's safe-install policy blocks (currently only installs with `--dangerously-force-unsafe-install`). Replace with `api.runtime.system.runCommandWithTimeout` (the sanctioned subprocess API per docs)."
status: active
stage: null
contribution: high
created: 2026-05-09
closed_at: null
human_gate: session
advances:
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `openclaw-plugin/tsconfig.json` emits compiled output (`noEmit: false`, `outDir: "./dist"`); `openclaw-plugin/dist/index.js` exists and matches `index.ts`
  - [x] `openclaw-plugin/package.json` declares `main: "./dist/index.js"`, `openclaw.extensions: ["./dist/index.js"]`, and scripts: `build`, `prepare` (auto-build after npm install), `prepublishOnly` (auto-build before npm publish)
  - [x] `openclaw-plugin/index.ts` no longer imports from `node:child_process`; subprocess invocations use `api.runtime.system.runCommandWithTimeout(cmd, args, opts)` per <https://docs.openclaw.ai/plugins/sdk-runtime.md>. `runGoc` helper is moved inside `register(api)` so it can capture `api.runtime` in its closure.
  - [x] Build artifact: `cd openclaw-plugin && npm install && npm run build` produces a `dist/index.js` that's committed to the repo.
  - [ ] Smoke retest by the original tester confirms: (a) `openclaw plugins install <local-path>` no longer fails for missing JS; (b) install no longer requires `--dangerously-force-unsafe-install`; (c) `openclaw plugins inspect game-of-cards --json` shows `toolNames: ["goc"]` populated; (d) a subagent invocation can see and call the `goc` tool.
  - [x] `uv run goc validate` passes.
  - [x] Side finding (out of this card's scope): website / `llms.txt` still recommends `uv tool install` as the install path. Reviewer (2026-05-09) decided the scope expansion is large enough to warrant a separate card rather than stretching `llms-txt-still-recommends-uv-tool-install-as-preferred`'s narrow uv→pipx fix. Resolved by filing `add-openclaw-install-section-to-llms-txt`.
worker: {who: "claude[bot]", where: main}
---

# OpenClaw plugin release-smoke blockers — build pipeline + sanctioned spawn API

## Action required (gate still session as of retest #2)

Implementation history:
- `7cb062c openclaw-plugin: ship compiled JS + sanctioned spawn API` (2026-05-09 PM) — α implementation, DoD items 1–4 and 6 checked.
- Retest #2 (2026-05-09 PM) — still red: scanner pattern-matches `child_process` token in source comments, not just imports. See log.md "retest #2" entry for root-cause walk.
- Comment-rephrase commit (this session) — both source comments rewritten to drop the trigger token; `dist/` rebuilt; `grep` confirms repo tree is clean.
- DoD item 7 ticked: side-finding (`add-openclaw-install-section-to-llms-txt`) filed as a separate card per reviewer's scope decision.

**One DoD item remains: item 5 (smoke retest #3).** Tester needs to rerun the install flow on an OpenClaw runtime and confirm:
- `openclaw plugins install <local-path>` succeeds **without** `--dangerously-force-unsafe-install` (no dangerous-code rejection).
- `openclaw plugins inspect game-of-cards --json` shows `imported: True`, `toolNames: ["goc"]`, `tools` non-empty.
- A subagent can see and invoke the `goc` tool.

The `TODO(verify-shape)` comments in `openclaw-plugin/index.ts` around `runCommandWithTimeout` and the three hook contexts can be resolved during this retest — the real OpenClaw SDK types confirm or correct our reasonable-guess assumptions.

Once retest #3 passes, call `goc decide openclaw-plugin-release-smoke-blockers-build-and-spawn-api --decision "..." --because "..."` to lower the gate to `none`, tick the last box, and `goc done` to close.

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
