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
