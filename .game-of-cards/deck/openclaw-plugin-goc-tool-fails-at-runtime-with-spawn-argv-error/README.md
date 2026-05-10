---
title: openclaw-plugin-goc-tool-fails-at-runtime-with-spawn-argv-error
summary: "OpenClaw plugin v0.0.7 ships a `goc` tool whose `runCommandWithTimeout` invocation uses an outdated 3-arg signature `(cmd, argv, opts)` instead of the unified 2-arg `(argv, opts)` the SDK has used since at least 2026.5.7. Calling the tool fails at runtime with `The 'args' argument must be of type object. Received type string ('ython3')`. A second latent defect: the result-field reader uses `result.exitCode` but OpenClaw exposes the field as `result.code`, so any non-zero exit silently coerces to 0 (success). Both defects survived release smoke because retests #1–#5 only inspected registration shape via `openclaw plugins inspect --runtime --json`, never invoking the tool."
status: done
stage: null
contribution: high
created: 2026-05-10
closed_at: 2026-05-10
human_gate: none
advances:
  - provide-openclaw-plugin-for-skills-and-hooks
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] `openclaw-plugin/index.ts` `runGoc()` calls `api.runtime.system.runCommandWithTimeout(["python3", "-m", "goc.cli", ...args], { cwd, env, timeoutMs: 60_000 })` — single argv array as first positional arg, options as second arg. Old `(cmd, argv, opts)` 3-arg form removed.
  - [x] `openclaw-plugin/index.ts` `runGoc()` reads exit code as `result.code ?? result.exitCode ?? 0` so the real field name (`code`, per `node_modules/openclaw/dist/exec-Kfr6njO_.js:306`) is preferred and `exitCode` remains a defensive fallback for forward compatibility.
  - [x] The `// TODO(verify-shape)` comment block above `runGoc()` is replaced with a one-line note pointing at the verified contract location (`exec-Kfr6njO_.js:165` for the signature, `:306` for the result schema).
  - [x] `cd openclaw-plugin && npm install && npm run build` regenerates `dist/index.js` with the fix; the bundle is committed.
  - [x] `python3 scripts/sync_plugin_assets.py` is a no-op (this fix only edits source files that are not auto-mirrored); `python3 scripts/sync_plugin_assets.py --check` passes.
  - [x] `uv run goc validate` passes.
  - [x] Card body documents the why-it-survived-smoke gap (registration introspection vs. invocation execution) so future smoke tests cover both code paths.
worker: {who: Rodja Trappe, where: main}
---

# OpenClaw plugin goc tool fails at runtime with spawn argv error

## Symptoms (reported 2026-05-10)

User report against shipped v0.0.7:

- `openclaw plugins inspect game-of-cards --runtime --json` reports `imported: True`, `toolNames: ['goc']`, hooks active. Registration looks healthy.
- Invoking the tool — `functions.goc({ verb: "validate", args: [] })` — fails immediately with:
  ```
  The "args" argument must be of type object. Received type string ('ython3')
  ```
- Manual patch in the installed plugin (replace 3-arg call with 2-arg call, plus `result.exitCode ?? result.code ?? 0`) restores `goc validate: OK`. Same symptom must also exist in v0.0.8–0.0.11 (no commits to `index.ts` between releases).

## Root cause

Two latent defects in `openclaw-plugin/index.ts:246-271`:

### 1. Wrong argv signature (the visible failure)

The plugin calls:
```ts
runCommandWithTimeout("python3", ["-m", "goc.cli", ...args], { cwd, env, timeoutMs })
```

But the actual SDK signature (verified in `node_modules/openclaw/dist/exec-Kfr6njO_.js:165`) is:
```ts
async function runCommandWithTimeout(argv, optionsOrTimeout)
```

A single argv array as first arg, options object (or numeric timeout) as second arg. With the old 3-arg call:
- `argv = "python3"` (a string)
- `optionsOrTimeout = ["-m", "goc.cli", ...]` (an array — interpreted as a falsy options object, then destructured to undefined fields)
- The third `{cwd, env, timeoutMs}` argument is silently discarded — meaning **even if the call had not crashed, cwd/env/timeoutMs were never honored**.

The `'ython3'` residual in the error message is forensic: downstream `argv.slice(1)` operates on a string, returning `"ython3"`, which is then handed to Node's `child_process.spawn(cmd, args)` as the `args` parameter — Node rejects strings-where-array-expected with that exact error message.

### 2. Wrong result field name (silent failure)

The plugin reads the exit code as:
```ts
exitCode: (result?.exitCode as number | undefined) ?? 0
```

But the SDK resolves with `code: normalizedCode` (verified at `exec-Kfr6njO_.js:306`), not `exitCode`. So `result.exitCode` is always undefined, and the `?? 0` fallback silently coerces every invocation — even genuine command failures — to a success result. Tool callers cannot distinguish success from failure.

This is a textbook silent-failure pattern: the defensive nullish-coalesce *looks* protective but actively hides real errors when paired with the wrong field name. The user's manual patch (`result.exitCode ?? result.code ?? 0`) fixes both the present (where `code` is the real field) and provides forward compatibility against another field rename.

## Why this survived release smoke

Looking at retests #1–#5 in the parent card `openclaw-plugin-release-smoke-blockers-build-and-spawn-api`: every retest inspected `openclaw plugins inspect game-of-cards --runtime --json` to confirm `imported: True` and `toolNames: ['goc']`. None of them actually **called** the tool. Registration shape and execution shape are independent contracts:

- The registration contract is verified by `inspect --runtime --json`.
- The execution contract requires invoking the tool against a real workspace.

Retest #5 even instrumented `register(api)` to confirm `api.registerTool({...})` ran to completion — but that confirms registration, not execution. The first time the tool was actually called against a deployed copy, the bug surfaced immediately.

The TODO comment in the source already flagged this as a guess:
> `// TODO(verify-shape): the precise signature of runCommandWithTimeout is not documented at the URL above (only the call shape ... is shown). The result is assumed to expose 'exitCode', 'stdout', and 'stderr' fields; smoke testing will confirm or correct.`

The smoke testing did not exercise the path that would have confirmed or corrected this guess.

## The fix (verified locally by the reporter)

```ts
const result = await api.runtime.system.runCommandWithTimeout(
  ["python3", "-m", "goc.cli", ...args],
  { cwd, env, timeoutMs: 60_000 },
);
return {
  exitCode: (result?.code as number | undefined) ?? (result?.exitCode as number | undefined) ?? 0,
  stdout: (result?.stdout as string | undefined) ?? "",
  stderr: (result?.stderr as string | undefined) ?? "",
};
```

Reporter verified after patching the installed plugin:
- `openclaw doctor --non-interactive`: OK
- `openclaw plugins inspect --runtime --json`: `imported: True`, `toolNames: ['goc']` (unchanged from v0.0.7)
- First-class `goc validate` invocation: OK

## Prevention follow-ups (not in scope for this card)

A future hardening card could add:
- A post-build smoke step that invokes `goc validate` through the registered tool (not just inspects registration).
- Type imports from `openclaw/plugin-sdk/runtime` for `runCommandWithTimeout` so the signature contract is type-checked at build time. (Today the source uses `api: any`, which is what allowed the wrong signature to compile silently.)

These are deliberately out of scope here so this card stays a focused bugfix.
