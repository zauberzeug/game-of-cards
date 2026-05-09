## 2026-05-09 (PM): build pipeline + spawn API swap landed

Both clusters fixed in one commit. Card returns `active → open` pending the smoke retest (DoD item 5, requires the original tester to rerun the install flow on an OpenClaw runtime).

### Cluster A — build pipeline

- `openclaw-plugin/tsconfig.json`: `noEmit: false`; `outDir: "./dist"`; `rootDir: "./"`; added `declaration: true` and `sourceMap: true`. Dropped `allowImportingTsExtensions` (incompatible with emit) and `verbatimModuleSyntax` (over-strict for our case). `exclude` adds `dist`.
- `openclaw-plugin/package.json`: added `main: "./dist/index.js"`, `types: "./dist/index.d.ts"`, `openclaw.extensions: ["./dist/index.js"]` (was `./index.ts`), and three scripts (`build`, `prepare`, `prepublishOnly`). `files` array now includes `dist/`.
- Top-level `.gitignore`: added negation `!openclaw-plugin/dist/` and `!openclaw-plugin/dist/**` to override the generic Python `dist/` ignore — the OpenClaw build artifact is a tracked output, not a .gitignored output.
- `openclaw-plugin/.gitignore`: dropped `dist/` from local ignores (was redundant with the parent rule, which is now negated for this subtree). Added a comment explaining the intent.
- Built locally: `cd openclaw-plugin && npm install` (562 packages, no vulnerabilities) + `npm run build` produced `dist/index.js`, `dist/index.d.ts`, `dist/index.js.map`. All three are committed.

### Cluster B — sanctioned subprocess API

- Removed `import { spawn } from "node:child_process";` from `openclaw-plugin/index.ts`.
- Moved `runGoc` helper inside `register(api)` so it can capture `api.runtime` in its closure (top-level functions can't reach the per-registration api object).
- Replaced the `spawn(...)` Promise wrapper with `await api.runtime.system.runCommandWithTimeout("python3", ["-m", "goc.cli", ...args], { cwd, env, timeoutMs: 60_000 })`. The result is unwrapped defensively (`?.exitCode ?? 0`, etc.) since the precise shape of the return value is undocumented at <https://docs.openclaw.ai/plugins/sdk-runtime.md> — flagged with a `TODO(verify-shape)` comment for the smoke retest.
- The three lifecycle hooks (`session_start`, `before_prompt_build`, `agent_end`) are unchanged — they read the local filesystem only, no subprocess calls.
- `PLUGIN_ROOT` recomputed: after compilation `index.js` lives at `openclaw-plugin/dist/index.js`, so `dirname(import.meta.url)` resolves to `dist/` and `PLUGIN_ROOT = resolve(dist, "..")` lifts back to `openclaw-plugin/` where the vendored `goc/` package lives.

### Smoke-test handoff

The remaining DoD item (5) is the tester's rerun. Once they confirm:

- `openclaw plugins install <local-path>` succeeds without `--dangerously-force-unsafe-install`
- `openclaw plugins inspect game-of-cards --json` shows `toolNames: ["goc"]` and `tools` populated (proving `register(api)` actually fired and `api.registerTool` succeeded)
- A subagent can see and invoke the `goc` tool

…the card is closeable (modulo the side-finding pointer about `llms.txt`, which lives on its own card and doesn't block close).

The `TODO(verify-shape)` markers on `runCommandWithTimeout` and the three hook contexts will resolve concretely during the smoke retest — that's when the real OpenClaw SDK types confirm or correct our reasonable-guess assumptions.

## 2026-05-09 (PM, follow-up): gate raised `none → session` for tester rerun

Pulled this card during a `pull-card` drain. Verified the implementation is in place:
`openclaw-plugin/dist/{index.js,index.d.ts,index.js.map}` are committed; `openclaw-plugin/index.ts` uses `api.runtime.system.runCommandWithTimeout` and no longer imports from `node:child_process`.

Of the two unchecked DoD items, neither is agent-actionable from this repo:

- **Item 5 (smoke retest)** is strictly a human action on an OpenClaw runtime — the agent has no path to install a plugin into OpenClaw and observe `openclaw plugins inspect`.
- **Item 7 (side-finding scope check)** is a coordination judgement about whether `llms-txt-still-recommends-uv-tool-install-as-preferred` should expand its scope. The reviewer is the right decider; expanding that card unilaterally would override the "one-comment edit" rationale in its `Why this is gate=none` body.

Raised `human_gate: none → session` and added an `## Action required` body section that names both pending items and the close path (`goc decide … --decision "…" --because "…"` → tick boxes → `goc done`). Per pull-card guidance, cards that raise their gate during the session leave the drain set naturally — a future pull won't re-claim this until the gate is lowered.

## 2026-05-09 (PM, retest #2): scanner pattern-matches the comment, not the import

Tester reran the smoke. Result: still red. Two observations from the report:

- `openclaw plugins install <local-path>` (without `--dangerously-force-unsafe-install`) is rejected by **dangerous-code detection on `child_process`**. The install was forced through with `--force` so the next observation could be made anyway.
- `openclaw plugins inspect game-of-cards --json` shows `status: loaded`, `contracts.tools: ['goc']`, `toolNames: []`, `tools: []`, `imported: False`. The static manifest's `contracts.tools` is read from `openclaw.plugin.json`; the empty dynamic surface (`toolNames`, `tools`) and `imported: False` are coherent: the scanner blocked module import, so `register(api)` never ran, so `api.registerTool` never registered the `goc` tool.

### Root cause

OpenClaw's safe-install scanner pattern-matches on **raw source bytes** — it does not parse the JS/TS as an AST, so a literal `child_process` token in a *comment* trips the same heuristic as an actual subprocess-module import line. The α implementation removed the import, but the architectural-rationale comments still spelled out the blocked-import name verbatim:

- `openclaw-plugin/index.ts:22` (top doc-block) — `` * `node:child_process` imports, which the safe-install policy blocks.``
- `openclaw-plugin/index.ts:236` (inline comment inside `register(api)`) — `// node:child_process directly.`
- Carry-over into `openclaw-plugin/dist/index.js` (lines 22, 212) and `openclaw-plugin/dist/index.d.ts` (line 22), since `tsc` preserves comments by default.

The scanner saw those substrings and refused to import the module — exactly the behavior `imported: False` reports.

### Fix

Rephrased both source comments so the architectural intent stays clear without spelling the trigger token:

- Top doc-block: "direct stdlib subprocess imports, which the safe-install policy blocks. (The blocked-import name is intentionally not spelled out here: OpenClaw's safe-install scanner pattern-matches on raw source bytes and trips on the literal token even when it appears only in a comment.)"
- Inline comment: "blocks plugins that directly import the Node stdlib subprocess module."

Rebuilt via `(cd openclaw-plugin && npm run build)`; `tsc` regenerated `dist/index.js`, `dist/index.js.map`, and `dist/index.d.ts`. Verified post-build:

```
$ grep -rn "child_process" openclaw-plugin/index.ts openclaw-plugin/dist/ openclaw-plugin/openclaw.plugin.json openclaw-plugin/package.json
(no matches; exit 1)
```

### Next

Same acceptance bar as before — but now with corrected `imported: False` expectation:

- `openclaw plugins install <local-path>` succeeds **without** `--dangerously-force-unsafe-install` (no dangerous-code rejection).
- `openclaw plugins inspect game-of-cards --json` shows `imported: True`, `toolNames: ["goc"]`, `tools` non-empty.
- A subagent can see and invoke the `goc` tool.

Gate stays `session` — DoD item 5 still requires the tester action; this commit only addresses *why* the previous retest failed. The `TODO(verify-shape)` markers on `runCommandWithTimeout` and the three hook contexts can still resolve during this retest.

### Side-finding (DoD item 7) — answered

Reviewer's call: **expand scope.** `site/llms.txt` should grow an OpenClaw-specific install section. That's a feature add (additive content), distinct from `llms-txt-still-recommends-uv-tool-install-as-preferred`'s narrow one-comment uv→pipx correction. Filed as a separate card so the existing card's gate-none "one-comment edit" rationale stays intact. Cross-reference: see `add-openclaw-install-section-to-llms-txt`.

## 2026-05-09 (PM, retest #3): scanner clear, but typebox is a runtime dep in the wrong section

Tester reran against `main` HEAD `8277962`. Result: better, still red.

### What's better

- `openclaw plugins install <local-path> --force` now runs **without** `--dangerously-force-unsafe-install`. Dangerous-code scanner is no longer tripping. Comment-rephrase from retest #2 worked.

### What's still red

- Install fails with: `Cannot find module '@sinclair/typebox'`.
- Root cause: `@sinclair/typebox` was declared in `devDependencies` of `openclaw-plugin/package.json`, but the compiled `dist/index.js` imports it at runtime (`import { Type, type Static } from "@sinclair/typebox"` in `index.ts:30`). When OpenClaw runs the plugin's prod-only dep install, devDependencies are skipped and the runtime import fails.

After tester manually installed typebox, the install proceeds further but `openclaw plugins inspect game-of-cards --json` still shows `imported: false`, `toolNames: []`, `tools: []`. Tester verified that direct Node import of `dist/index.js` with a mock API DOES call `api.registerTool({ name: "goc" })` — so the registration code is correct end-to-end; the gap is somewhere in OpenClaw's loader between "module file resolved" and "register(api) executed".

### Fix

Moved `@sinclair/typebox: ^0.32.0` from `devDependencies` to a new `dependencies` block in `openclaw-plugin/package.json`. Ran `npm install` to refresh the lockfile (`prepare` script auto-rebuilt `dist/`).

After this lands, the next plugin install should pull typebox automatically — the tester won't need to manual-install. If `imported: false` persists post-fix, the next debugging pass should look at OpenClaw's plugin install/load logs (verbose mode) for the explicit failure, since the plugin entry shape (`export default definePluginEntry({...})`) matches the canonical example in `node_modules/openclaw/docs/plugins/building-plugins.md`. Likely candidate causes if it persists: (a) OpenClaw caches the prior load failure across the inspect call even after the dep is satisfied, (b) OpenClaw's installed-plugin location differs from where the tester manually installed typebox, so the runtime resolver still can't find it.

### Hypothesis for `imported: false` even with typebox available

Reading `node_modules/openclaw/dist/loader-B-GXgDrk.js` and `status-DEJL5ql6.js`: the `imported` flag in `inspect --json` becomes `true` when the loader reaches `recordImportedPluginId(record.id)` immediately before `loadPluginModule(safeSource)`. If `loadPluginModule` throws (e.g., `Cannot find module '@sinclair/typebox'`), the id is recorded as imported BUT the registration never fires, leaving `tools: []` / `toolNames: []`. The tester's report shows `imported: false`, which suggests we never reached `recordImportedPluginId` — i.e., we bailed earlier (manifest validation, configSchema check, or `openBoundaryFileSync` rejecting the entry path with `rejectHardlinks: true` for external plugins). Once typebox lands as a real dep, retest with verbose logging (`OPENCLAW_LOG_LEVEL=debug` or equivalent) to see which `pushPluginLoadError` path fires.

### Next

Same acceptance bar as retest #2:
- `openclaw plugins install <local-path>` succeeds without `--dangerously-force-unsafe-install` AND without manual `npm install @sinclair/typebox` afterward.
- `openclaw plugins inspect game-of-cards --json` shows `imported: True`, `toolNames: ["goc"]`, `tools` non-empty.
- A subagent can see and invoke the `goc` tool.

DoD item 5 stays unchecked.
