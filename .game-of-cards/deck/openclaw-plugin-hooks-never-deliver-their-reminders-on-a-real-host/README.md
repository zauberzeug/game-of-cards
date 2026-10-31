---
title: openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host
summary: "The three OpenClaw lifecycle hooks in openclaw-plugin/index.ts were written against guessed SDK shapes (TODO(verify-context-shape)), and none matches OpenClaw 2026.5.7, the version the plugin's lockfile pins: the host calls handler(event, ctx) and merges before_prompt_build's return value, while the handlers read userPrompt / projectDir / toolCalls off the event and deliver through notify / appendSystemContext methods no event carries. On a real host the deck-first reminder, the active-card reminder and the pattern check never reach the agent, and session_start and agent_end are fire-and-forget hooks with no channel to deliver through at all."
status: open
stage: null
contribution: high
created: "2026-10-31T05:15:01Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: the decision below is recorded via goc decide — a delivery channel for each of the three messages, checked against the compat floor in openclaw-plugin/package.json
  - [ ] TDD: reproduce.py exits zero (every registered hook reads only fields the SDK declares, and the deck-first reminder reaches the host in an opted-in workspace)
  - [ ] TDD: each handler is driven with the SDK's (event, ctx) shape, and the tests assert what reaches the host — the message in an opted-in workspace, nothing without a deck; tests/test_openclaw_prompt_hook.py moves to that shape
  - [ ] MECHANICAL: openclaw-plugin/dist/ is rebuilt, and the TODO(verify-context-shape) comments in index.ts and the Status note in openclaw-plugin/README.md give way to the verified shapes
---

# OpenClaw plugin hooks never deliver their reminders on a real host

## Location

- `openclaw-plugin/index.ts:715` — `session_start`: reads `ctx.projectDir`
  (`:716`), delivers through `ctx.notify` / `ctx.appendSystemContext`
  (`:745`, `:747`).
- `openclaw-plugin/index.ts:763` — `before_prompt_build`: reads
  `ctx.userPrompt` (`:764`), delivers through `ctx.appendSystemContext`
  (`:773`) or `ctx.prependSystemContext`.
- `openclaw-plugin/index.ts:797` — `agent_end`: reads `ctx.projectDir`
  (`:798`) and `ctx.toolCalls` / `ctx.events.toolCalls` (`:808`), delivers
  through `ctx.notify` / `ctx.appendSystemContext` (`:819`, `:821`).
- The SDK side, in `openclaw@2026.5.7` (the version
  `openclaw-plugin/package-lock.json` pins; `npm ci` in `openclaw-plugin/`
  installs it):
  - `dist/plugin-sdk/src/plugins/hook-types.d.ts:553,562,579` — handler
    signatures.
  - `hook-before-agent-start.types.d.ts:17-36` — the prompt-build event and
    result.
  - `dist/hook-runner-global-CCAcWVdN.js:304-336` — `runModifyingHook`.
  - `:280-298` — `runVoidHook`.

## What's broken

Each handler takes one argument and treats it as a context object with the
fields and methods it needs. The comments above two of them say the shape is
a guess:

```ts
// TODO(verify-context-shape): the session_start handler context is not
// documented at https://docs.openclaw.ai/plugins/hooks.md beyond
// "track session lifecycle boundaries". The fields used below
// (ctx.projectDir, ctx.notify) are reasonable guesses ...
api.on("session_start", async (ctx: any) => {
  const projectDir = (ctx?.projectDir as string | undefined) ?? process.cwd();
...
api.on("before_prompt_build", async (ctx: any) => {
  const prompt = ((ctx?.userPrompt as string | undefined) ?? "").toLowerCase();
  if (!prompt) return;
  ...
  if (typeof ctx?.appendSystemContext === "function") {
    ctx.appendSystemContext(DECK_REMINDER);
```

The SDK the plugin builds against calls every typed hook with two arguments
and reads only the return value:

```ts
before_prompt_build: (event: PluginHookBeforePromptBuildEvent, ctx: PluginHookAgentContext)
    => Promise<PluginHookBeforePromptBuildResult | void> | ...;
agent_end:     (event: PluginHookAgentEndEvent, ctx: PluginHookAgentContext) => Promise<void> | void;
session_start: (event: PluginHookSessionStartEvent, ctx: PluginHookSessionContext) => Promise<void> | void;

export type PluginHookBeforePromptBuildEvent = { prompt: string; messages: unknown[]; };
export type PluginHookBeforePromptBuildResult = { systemPrompt?: string; prependContext?: string;
    appendContext?: string; prependSystemContext?: string; appendSystemContext?: string; };
```

`runModifyingHook` runs `handler(event, ctx)` and merges whatever it returns.
`runVoidHook`, which runs `session_start` and `agent_end`, is fire-and-forget:
it awaits the handler and discards the result. No event carries `userPrompt`,
`projectDir`, `toolCalls`, `notify` or `appendSystemContext`. Against this
SDK:

- `before_prompt_build` reads `event.userPrompt` (absent), so `prompt` is
  empty and the handler returns at once. The deck-first reminder never fires,
  in any workspace.
- `session_start` falls back to `process.cwd()`, the gateway's directory,
  because the event has no `projectDir`. It finds no `notify` or
  `appendSystemContext` to deliver through. A void hook has no channel in any
  case. The session context (`agentId`, `sessionId`, `sessionKey`) carries no
  workspace at all.
- `agent_end` reads no tool calls (`event.toolCalls` is absent; the turn is in
  `event.messages`), so it never sees a mutation. It is a void hook too, so
  the pattern reminder has no channel either. It is also a conversation hook,
  dropped for non-bundled plugins unless the operator sets
  `allowConversationAccess`, as the README already says.

The second argument, which holds `workspaceDir` for the two agent hooks, is
never read.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host/reproduce.py
openclaw-plugin/dist/index.js, each hook called as OpenClaw 2026.5.7 calls it:
  session_start        reads undeclared: event.projectDir, event.notify, event.appendSystemContext
                       returns to host:  null
  before_prompt_build  reads undeclared: event.userPrompt
                       returns to host:  null
  agent_end            reads undeclared: event.projectDir, event.toolCalls, event.events
                       returns to host:  null
deck-first reminder reaches the host in an opted-in workspace: False
DEFECT FIRES: the hooks read guessed fields and deliver nothing on a real host.
```

(exit 1)

The workspace in that run holds a deck with an active card. It also opts into
the pattern check, and it is the process cwd, so every handler has what it
needs to speak.

The real hook runner gives the same result. With `npm ci` run in
`openclaw-plugin/`, the compiled `dist/index.js` was registered into the SDK's
own runner (`initializeGlobalHookRunner` from `hook-runner-global-*.js`). Then
`runBeforePromptBuild({ prompt: "please fix the login redirect bug", messages: [] }, { workspaceDir })`
returned `undefined`, with a deck in the workspace. Calling the same handler
with the guessed shape (`{ userPrompt, appendSystemContext }`) appends the
reminder.

## Why it matters

- **OpenClaw gets the skills and the `goc` tool, and none of the methodology
  runtime.** It gets no deck-first nudge, no active-card reminder at session
  start, and no pattern check. The fixes already landed or filed against these
  handlers change code a real host never reaches. That covers the deck guard
  from
  [openclaw-prompt-hook-fires-in-workspaces-without-a-deck](../openclaw-prompt-hook-fires-in-workspaces-without-a-deck/),
  [openclaw-pattern-check-never-fires-on-plain-file-edits](../openclaw-pattern-check-never-fires-on-plain-file-edits/),
  [openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution](../openclaw-resolve-deck-dir-ignores-git-worktree-shared-deck-resolution/),
  and the session-start fixes to `isImpeded` and the frontmatter reader.
- **The goc tool's cwd fallback is the gateway's cwd.** `session_start` stores
  `sessionProjectDir`, which the tool uses when the agent passes no usable
  `cwd`. On a real host that value is always the gateway's `process.cwd()`,
  because the session event carries no project dir. That bears on
  [goc-tool-files-cards-into-wrong-agents-deck-on-multi-agent-gateways](../goc-tool-files-cards-into-wrong-agents-deck-on-multi-agent-gateways/).
  The SDK puts the workspace in `PluginHookAgentContext.workspaceDir` and in
  the tool factory context (`OpenClawPluginToolContext.workspaceDir`,
  `tool-types.d.ts:15`).
- **The docs claim working hooks.** `openclaw-plugin/README.md` lists "3
  lifecycle hooks — fire automatically". The closed
  [openclaw-plugin-release-smoke-blockers-build-and-spawn-api](../openclaw-plugin-release-smoke-blockers-build-and-spawn-api/)
  states that the plugin "still works for tool calls and the other two hooks".

## Decision required

The `before_prompt_build` port is mechanical. Take `(event, ctx)`, read
`event.prompt`, and look the deck up on
`ctx.workspaceDir ?? sessionProjectDir ?? process.cwd()`. Then return
`{ appendSystemContext: DECK_REMINDER }`, the field the handler already
prefers. Three questions stay open:

1. **Where do the two void-hook messages go?** `session_start` and
   `agent_end` cannot hand anything back to the host.
2. **Rollout.** Fixing the shapes switches on reminders that have never fired
   in a live OpenClaw deployment. The active card
   [openclaw-plugin-skills-force-repeated-reads-every-session](../openclaw-plugin-skills-force-repeated-reads-every-session/)
   is waiting on a before/after trajectory count from such a deployment, and
   newly firing reminders would confound that count.
3. **Compat floor.** `openclaw-plugin/package.json` declares
   `pluginApi >=2026.3.24-beta.2`. Nobody has checked whether the surfaces
   named below exist at that floor.

**A. Port each hook to its nearest SDK channel.**

- `before_prompt_build`: as above.
- `session_start`: queue the active-card reminder with
  `api.enqueueNextTurnInjection(...)`
  (`dist/plugin-sdk/src/plugins/types.d.ts:1996`).
- `agent_end`: move the pattern check to `before_agent_finalize`, returning
  `{ action: "revise", reason: PATTERN_REMINDER }` when `event.messages` show
  a mutating tool call. `event.stopHookActive` guards the loop, which is the
  shape of the Claude Code `Stop` hook it ports (`hook-types.d.ts:114-140`).

Pro: each message keeps its timing (session boot, before yielding). Con:
three SDK surfaces, two of them possibly above the floor. `session_start`
still has no workspace to find the deck in.

**B. Put both reminders in `before_prompt_build`.** One prompt-time handler
reads `ctx.workspaceDir` and `ctx.sessionId`. It adds the active-card reminder
on a session's first turn and the deck-first reminder on work-shaped prompts.
It adds the pattern reminder on the turn after one that mutated, recorded from
`agent_end`'s `event.messages`. Pro: one channel, and the workspace is known.
Con: per-session state, and the pattern check arrives a turn late, after the
user's next prompt rather than before the agent yields.

**C. Ship only the mechanical `before_prompt_build` port.** Drop the
`session_start` and `agent_end` handlers and their README rows until a channel
is chosen. Pro: the smallest change, and the docs become accurate. Con: OpenClaw
loses the active-card reminder and the pattern check for now.

**Recommendation:** B for the active-card reminder (`session_start` cannot see
a workspace), A's `before_agent_finalize` revise for the pattern check (the
`Stop` hook's direct analogue), and land the `before_prompt_build` port first.
