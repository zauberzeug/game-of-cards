---
title: openclaw-prompt-hook-fires-in-workspaces-without-a-deck
summary: "The OpenClaw plugin's before_prompt_build handler appended the deck-first reminder to every work-shaped prompt without looking for a deck, so it claimed \"runtime active\" in workspaces that never opted in, the gap deck_prompt_router.py had already closed on the Python side. It now returns unless the session's project dir holds .game-of-cards/deck/ or the legacy deck/, with tests/test_openclaw_prompt_hook.py pinning the guard and dist/ rebuilt. On the pinned OpenClaw SDK the handler still delivers nothing in any workspace, because it reads a guessed context shape, and openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host tracks that."
status: done
stage: null
contribution: medium
created: "2026-10-24T04:33:31Z"
closed_at: "2026-10-31T05:22:57Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (the before_prompt_build handler consults a deck before appending DECK_REMINDER)
  - [x] TDD: a regression test runs the handler logic (extracted from index.ts under `node --experimental-strip-types`, as tests/test_openclaw_session_start_hook.py does) and asserts no reminder for a work-shaped prompt in a directory without a deck, and the reminder, unchanged, in one with `.game-of-cards/deck/`
  - [x] MECHANICAL: openclaw-plugin/dist/ is rebuilt from the edited index.ts (`npm run build` in openclaw-plugin/) and committed with it
  - [x] MECHANICAL: the sentence in AGENTS.md naming this card as the open gap (the paragraph "Every runtime hook is inert in a repo that never opted in") is rewritten to state that the OpenClaw port carries the guard too, and openclaw-plugin/README.md's hook table says the reminder is silent without a deck
worker: {who: "claude[bot]", where: main}
---

# OpenClaw's prompt hook injects the deck-first reminder in workspaces without a deck

## Location

- `openclaw-plugin/index.ts:763` — the `api.on("before_prompt_build", …)`
  handler. It reads `ctx.userPrompt`, runs the work / exploration / tooling
  patterns, and appends `DECK_REMINDER` (`index.ts:399`). Before the fix it
  never touched the filesystem. The guard is now at `index.ts:771`.
- The guard uses helpers that already sat in the same file:
  `hasDeck(projectDir)` (`index.ts:569`, canonical `.game-of-cards/deck` or
  legacy `deck`) and `sessionProjectDir` (`index.ts:632`). `session_start`
  stores the session's project dir in `sessionProjectDir` from
  `ctx.projectDir ?? process.cwd()`. Its own deck lookup is
  `resolveDeckDir` (`index.ts:351`).

## What's broken

The handler's own header comment says it "was deck_prompt_router.py", and
the patterns above it are commented "mirror
goc/templates/hooks/deck_prompt_router.py exactly". The Python router now
returns silently unless the session's project root holds a deck. The fix
for [runtime-hooks-fire-in-repos-that-never-opted-in](../runtime-hooks-fire-in-repos-that-never-opted-in/)
did that and stated the rule in AGENTS.md: "Every runtime hook is inert in
a repo that never opted in." The TypeScript port did not get the same
guard:

```ts
api.on("before_prompt_build", async (ctx: any) => {
  const prompt = ((ctx?.userPrompt as string | undefined) ?? "").toLowerCase();
  if (!prompt) return;
  const hasWork = WORK_INITIATING.some((re) => re.test(prompt));
  ...
  if (!hasWork) return;
  if (typeof ctx?.appendSystemContext === "function") {
    ctx.appendSystemContext(DECK_REMINDER);
```

So in every OpenClaw workspace, opted in or not, a work-shaped prompt got
the "[Game of Cards | runtime active]" claim and the instruction to run the
card pipeline silently. The other two OpenClaw handlers are already inert
there. `session_start` finds no active cards without a deck, and
`agent_end` needs the explicit `hooks.pattern_generalization_check` switch
in `.game-of-cards/config.yaml`.

## Empirical evidence

Before the fix (exit 1):

```
$ uv run python .game-of-cards/deck/openclaw-prompt-hook-fires-in-workspaces-without-a-deck/reproduce.py
openclaw-plugin/index.ts:749 before_prompt_build handler
  appends DECK_REMINDER:  True
  consults a deck first:  False
DEFECT FIRES: the reminder is injected in every workspace, opted in or not.
```

After the fix (exit 0):

```
openclaw-plugin/index.ts:763 before_prompt_build handler
  appends DECK_REMINDER:  True
  consults a deck first:  True
ok: the reminder is gated on a deck.
```

The reproducer only reads the handler's source. The behavior is pinned by
`tests/test_openclaw_prompt_hook.py`, which runs the extracted handler
against real temporary directories. Run against the pre-fix `index.ts`, 3
of its 7 node subtests fail: no deck, a `.game-of-cards/` without its
`deck/`, and the process-cwd fallback without a deck. All 7 pass on the
fixed source.

## Why it matters

This is the same opt-in breach the Python card fixed, on the OpenClaw host.
The reminder's false "runtime active" claim makes the agent trust the hook
over the filesystem. It then tries to file and claim cards in a workspace
that never chose GoC. `goc new` now refuses without a deck and points at
`goc install` / `Skill(kickoff)`, so the agent is steered toward installing
the methodology. That should happen only when the user asks for it.

## Fix (applied)

The `before_prompt_build` handler now has one more line after
`if (!hasWork) return;`, so non-work prompts still never touch the disk:

```ts
if (!(await hasDeck(sessionProjectDir ?? process.cwd()))) return;
```

That is the project dir the `session_start` handler reads and the `goc`
tool defaults to (`params.cwd ?? sessionProjectDir ?? process.cwd()`).
`hasDeck` accepts the same canonical-or-legacy pair the Python hooks
accept. The fix also includes the following:

- `dist/` is rebuilt with `npm run build`. The `dist/index.js` diff is that
  one line, and a rebuild of the unedited source was byte-identical.
- `tests/test_openclaw_prompt_hook.py` is the regression test.
- The AGENTS.md sentence and the hook row in `openclaw-plugin/README.md` are
  updated.

Neither OpenClaw handler walks up to an ancestor holding `.game-of-cards/`
the way the engine and the Python hooks' `_find_project_dir` do. That gap is
separate and stays open.

**The guard does not change what a real OpenClaw host sees today.** The
pinned SDK (`openclaw@2026.5.7`) calls the handler as `handler(event, ctx)`
with `event.prompt` and reads only its return value. The handler reads
`userPrompt` and calls `appendSystemContext()` on its single argument, so on
a real host it returns before the guard and delivers nothing, in any
workspace. The guard keeps the handler inert where nobody opted in once the
shapes are fixed. That port should look the deck up on
`ctx.workspaceDir ?? sessionProjectDir ?? process.cwd()`. It is tracked by
[openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host](../openclaw-plugin-hooks-never-deliver-their-reminders-on-a-real-host/)
(`human_gate: decision`).
