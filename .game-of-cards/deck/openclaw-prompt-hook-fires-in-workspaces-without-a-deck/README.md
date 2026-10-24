---
title: openclaw-prompt-hook-fires-in-workspaces-without-a-deck
summary: "The OpenClaw plugin's before_prompt_build handler appends the deck-first reminder on every work-shaped prompt without looking for a deck, so it claims \"runtime active\" in workspaces that never opted in. Its Python counterpart deck_prompt_router.py was gated on deck presence by runtime-hooks-fire-in-repos-that-never-opted-in; the TypeScript port in openclaw-plugin/index.ts needs the same guard."
status: open
stage: null
contribution: medium
created: "2026-10-24T04:33:31Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (the before_prompt_build handler consults a deck before appending DECK_REMINDER)
  - [ ] TDD: a regression test runs the handler logic (extracted from index.ts under `node --experimental-strip-types`, as tests/test_openclaw_session_start_hook.py does) and asserts no reminder for a work-shaped prompt in a directory without a deck, and the reminder, unchanged, in one with `.game-of-cards/deck/`
  - [ ] MECHANICAL: openclaw-plugin/dist/ is rebuilt from the edited index.ts (`npm run build` in openclaw-plugin/) and committed with it
  - [ ] MECHANICAL: the sentence in AGENTS.md naming this card as the open gap (the paragraph "Every runtime hook is inert in a repo that never opted in") is rewritten to state that the OpenClaw port carries the guard too, and openclaw-plugin/README.md's hook table says the reminder is silent without a deck
---

# OpenClaw's prompt hook injects the deck-first reminder in workspaces without a deck

## Location

- `openclaw-plugin/index.ts:749` — the `api.on("before_prompt_build", …)`
  handler. It reads only `ctx.userPrompt`, runs the work / exploration /
  tooling patterns, and appends `DECK_REMINDER` (`index.ts:391`). It never
  touches the filesystem.
- The helpers a guard needs already sit in the same file:
  `hasDeck(projectDir)` (`index.ts:561`, canonical `.game-of-cards/deck` or
  legacy `deck`) and `resolveDeckDir(projectDir)` (`index.ts:343`, which the
  `session_start` handler uses). `sessionProjectDir` (`index.ts:624`) is
  the session's project dir, stored by `session_start` from
  `ctx.projectDir ?? process.cwd()`.

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

So in every OpenClaw workspace, opted in or not, a work-shaped prompt gets
the "[Game of Cards | runtime active]" claim and the instruction to run the
card pipeline silently. The other two OpenClaw handlers are already inert
there. `session_start` finds no active cards without a deck, and
`agent_end` needs the explicit `hooks.pattern_generalization_check` switch
in `.game-of-cards/config.yaml`.

## Empirical evidence

```
$ uv run python .game-of-cards/deck/openclaw-prompt-hook-fires-in-workspaces-without-a-deck/reproduce.py
openclaw-plugin/index.ts:749 before_prompt_build handler
  appends DECK_REMINDER:  True
  consults a deck first:  False
DEFECT FIRES: the reminder is injected in every workspace, opted in or not.
```

(exit 1)

## Why it matters

This is the same opt-in breach the Python card fixed, on the OpenClaw host.
The reminder's false "runtime active" claim makes the agent trust the hook
over the filesystem. It then tries to file and claim cards in a workspace
that never chose GoC. `goc new` now refuses without a deck and points at
`goc install` / `Skill(kickoff)`, so the agent is steered toward installing
the methodology. That should happen only when the user asks for it.

## Fix

In the `before_prompt_build` handler, after the `if (!hasWork) return;`
line (so non-work prompts still never touch the disk), add:

```ts
if (!(await hasDeck(sessionProjectDir ?? process.cwd()))) return;
```

That is the project dir the `session_start` handler reads and the `goc`
tool defaults to (`params.cwd ?? sessionProjectDir ?? process.cwd()`).
`hasDeck` accepts the same canonical-or-legacy pair the Python hooks
accept. Then rebuild `dist/` and add the regression test. Neither OpenClaw
handler walks up to an ancestor holding `.game-of-cards/` the way the
engine and the Python hooks' `_find_project_dir` do. That gap is separate,
and this card does not need to close it. If it bites, file it as its own
card.
