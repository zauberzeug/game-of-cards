---
title: openclaw-plugin-manifest-config-options-do-not-behave-as-documented
summary: "The OpenClaw plugin manifest's `configSchema` declares two settable options, and neither behaves as advertised: `deck_path` is read by nothing (not `index.ts`, not the committed `dist/index.js`, not the vendored engine), and `pattern_generalization_check` declares `default: true` while the README, the `index.ts` comment, and the runtime gate all say the hook is off unless explicitly enabled. Because `additionalProperties: false` makes this schema the complete set of keys OpenClaw accepts, an operator reading it has no other source of truth — setting `deck_path` silently no-ops, and the declared default may flip a hook on that every other surface promises is off."
status: open
stage: null
contribution: medium
created: "2026-07-30T05:24:16Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra, documentation]
definition_of_done: |
  - [ ] PROCESS: decision recorded below for `deck_path` — implement the override, or delete the key
  - [ ] TDD: `reproduce.py` exits 1 (both claims falsified)
  - [ ] TDD: a regression test asserts every `configSchema.properties` key of `openclaw.plugin.json` is referenced by at least one consumer (`index.ts` / `dist/index.js` / `goc/engine.py`), so the next added key cannot ship unwired
  - [ ] TDD: a regression test asserts `pattern_generalization_check`'s declared `default` matches the runtime gate's default (currently OFF)
  - [ ] MECHANICAL: `openclaw.plugin.json` and `openclaw-plugin/README.md` agree on the default for every declared key
  - [ ] MECHANICAL: `python3 scripts/port_skills_to_openclaw.py --check` and `python scripts/sync_plugin_assets.py --check` stay clean; `uv run goc validate` passes
---

# OpenClaw plugin manifest config options do not behave as documented

## Location

- `openclaw-plugin/openclaw.plugin.json:29-43` — the `configSchema` block
- `openclaw-plugin/openclaw.plugin.json:31` — `"additionalProperties": false`
- `openclaw-plugin/openclaw.plugin.json:33-36` — `deck_path`
- `openclaw-plugin/openclaw.plugin.json:37-41` — `pattern_generalization_check`
- `openclaw-plugin/index.ts:333-341` — `resolveDeckDir`
- `openclaw-plugin/index.ts:585-597` — `isEnabled` and its "default off" contract
- `openclaw-plugin/index.ts:772-777` — the `agent_end` runtime gate
- `openclaw-plugin/README.md:52` — the hook table's stated default
- `goc/engine.py:121-143` — `_resolve_deck_dir`, the engine's deck resolution

## What's broken

`openclaw.plugin.json` declares exactly two operator-settable options.
Neither one does what the schema says.

### 1. `deck_path` is a dead knob

```json
"configSchema": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "deck_path": {
      "type": "string",
      "description": "Override the per-workspace deck location. Defaults to <workspace>/.game-of-cards/deck/."
    },
```

Nothing reads it. The plugin's own deck resolution hardcodes the path
(`openclaw-plugin/index.ts:333`):

```ts
async function resolveDeckDir(projectDir: string): Promise<string> {
  const primary = resolve(projectDir, ".game-of-cards", "deck");
  try {
    await readdir(primary);
    return primary;
  } catch {
    return resolve(projectDir, "deck");
  }
}
```

No config parameter reaches this function, and the `goc` tool handler
passes only a `cwd` to `python3 -m goc.cli` — so the engine resolves the
deck itself, and it has no override either
(`goc/engine.py:121-143`):

```python
def _resolve_deck_dir(repo_root: Path) -> Path:
    ...
    canonical = repo_root / ".game-of-cards" / "deck"
    legacy = repo_root / "deck"
```

The string `deck_path` (or a `deckPath` camelCase spelling) does not
occur in `index.ts`, in the committed runtime bundle
`openclaw-plugin/dist/index.js`, or in `goc/engine.py`. Its only
occurrence anywhere outside a mirror tree is the manifest declaration
itself.

### 2. `pattern_generalization_check` declares the opposite default

```json
"pattern_generalization_check": {
  "type": "boolean",
  "default": true,
  "description": "Whether the agent_end hook reminds the model to consider filing generalization cards after code-mutating turns."
}
```

Every other surface says the hook is **off** unless explicitly enabled.
`openclaw-plugin/index.ts:585-587`:

```ts
// Opt-in (default off): the GoC project config must explicitly enable the
// hook with a YAML-true value. Absent config, absent key, `false`, or any
// other value leaves it disabled.
```

`openclaw-plugin/index.ts:776-777` — the gate short-circuits on anything
that is not literally `true`:

```ts
if (!(await isEnabled(projectDir)) &&
    ctx?.config?.pattern_generalization_check !== true) return;
```

And `openclaw-plugin/README.md:52` tells the operator:

> After code-mutating turns, prompts the model to consider filing a
> generalization card. Off by default; enable with
> `hooks.pattern_generalization_check: true` in `.game-of-cards/config.yaml`

A JSON-Schema `default` is the value a host materializes when the key is
absent. If OpenClaw materializes it — the normal reason to write one —
then `ctx.config.pattern_generalization_check === true` with no operator
action, the gate passes, and the hook fires by default: the exact
opposite of the documented contract, and it would also make the
`.game-of-cards/config.yaml` opt-in path (`isEnabled`) unreachable
dead code. If OpenClaw does not materialize it, the advertised default
is simply false advertising. There is no reading under which the
declaration is correct.

## Empirical evidence

`uv run python .game-of-cards/deck/openclaw-plugin-manifest-config-options-do-not-behave-as-documented/reproduce.py`:

```
openclaw.plugin.json configSchema
  additionalProperties : False
  declared keys        : deck_path, pattern_generalization_check

CLAIM 1 - declared config keys vs. code that reads them
  deck_path                        *** NEVER READ ***
  pattern_generalization_check     READ by openclaw-plugin/index.ts, openclaw-plugin/dist/index.js
  -> dead knobs: ['deck_path']

CLAIM 2 - declared default vs. every surface that states one
  openclaw.plugin.json 'default'          : True
  README.md says off by default           : True
  index.ts comments 'default off'         : True
  index.ts gate skips unless === true     : True

CLAIM 1 reproduced (deck_path is a dead knob)      : True
CLAIM 2 reproduced (default: true vs. default off) : True

DEFECT PRESENT
```

The reader test is deliberately generous — any mention of the key in
either snake_case or camelCase, anywhere in a consumer file, counts as
"read". `deck_path` fails even that bar.

## Why it matters

`additionalProperties: false` makes this schema the *complete* set of
keys OpenClaw will accept for the plugin. That turns it into the
operator's only source of truth for what is configurable, and both
entries mislead:

- Setting `deck_path` produces no validation error (it is declared) and
  no effect (nothing reads it). The operator's deck stays wherever it
  was, with nothing to explain why. This is worse than an undeclared
  key, which would at least be rejected.
- The `default: true` either silently flips a hook on that three other
  surfaces promise is off, or lies about what happens when the key is
  omitted. Which of the two depends on host behavior the plugin does not
  control — so the declaration is wrong either way.

The root cause is the same for both: `openclaw.plugin.json` is
explicitly **not** auto-synced (AGENTS.md § "OpenClaw plugin payload"),
and no guard connects its `configSchema` to the code. This is the same
hand-maintained-enumeration shape already tracked for the manifest's
`skills` array by
[derive-openclaw-manifest-skills-array-from-ported-skill-dirs](../derive-openclaw-manifest-skills-array-from-ported-skill-dirs/)
— that card's parity guard covers `skills` only and would not have
caught either of these. The two cards are siblings in the same file, not
duplicates: this one is about the config contract, that one about skill
registration.

Sibling sweep: neither `claude-plugin/.claude-plugin/plugin.json` nor
`codex-plugin/.codex-plugin/plugin.json` declares a `configSchema`, so
the defect is confined to the OpenClaw payload. No third instance, so
no architectural meta-fix is warranted yet.

## Decision required

**`pattern_generalization_check` needs no decision** — every other
surface agrees the hook is off by default, so the manifest is the
outlier. Change `"default": true` to `"default": false` (or drop the
`default` key, letting the runtime gate be the single source of truth;
an explicit `false` is preferable because it documents the contract).

**`deck_path` does need one.** Two credible paths:

**Option A — delete the key.** The plugin does not support a deck-path
override, so stop advertising one. One-line manifest edit, no runtime
change, and `additionalProperties: false` then correctly rejects the key
instead of silently swallowing it. Cost: an operator who has already set
`deck_path` gets a validation error on their next plugin load — loud,
but loud about something that never worked.

**Option B — implement the override.** Thread the config value through
`resolveDeckDir` for the hooks, and through the `goc` tool handler for
the engine. The engine half is the expensive part: `goc/engine.py`
resolves `DECK_DIR` at *import* time from module-level globals
(`goc/engine.py:146-147`), so an override needs either a new env var the
plugin sets before spawning, or a CLI flag — a change to the engine's
public surface, not just the plugin's. That work overlaps the active
epic
[support-external-game-of-cards-state-location](../support-external-game-of-cards-state-location/),
which is parked at `human_gate: session` precisely because where GoC
state lives is a maintainer call.

**Recommendation: Option A now**, and let the epic decide whether a
deck-path override exists at all. Deleting a knob that has never worked
costs nothing and stops the manifest from promising a feature the epic
has not yet decided to build. If the maintainer wants the override, the
right home is the epic, with the manifest key re-added once the engine
surface exists.

Either way, the durable fix is the guard: a regression test that walks
`configSchema.properties` and fails when a declared key has no consumer,
plus one that pins each declared `default` to the runtime gate's actual
default. Without it, key number three ships unwired the same way.
