---
title: plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine
summary: "The plugin bin/goc wrappers and the OpenClaw tool handler ran \"python3 -m goc.cli\", and -m puts the invocation cwd at sys.path[0], ahead of the plugin root — so a consumer repo's top-level goc/ package took over the goc command and a repo-root module shadowing a stdlib name crashed it. Every plugin start and the engine's own re-invocation now run goc/_launch.py by absolute path, which swaps sys.path[0] for the plugin root before anything else is imported; this holds on the Python 3.10 floor."
status: done
stage: null
contribution: high
created: "2026-09-10T04:50:58Z"
closed_at: "2026-10-25T05:24:19Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] DECISION: pick the isolation mechanism given the Python 3.10 floor — `-P` / `PYTHONSAFEPATH` are 3.11+, so either raise the floor, branch on version, or stop using `-m` (see `## Decision`)
  - [x] TDD: `reproduce.py` exits zero — a cwd-local `goc/` package no longer replaces the bundled engine for either wrapper
  - [x] TDD: a regression test covers the stdlib-shadowing variant (a repo-root module named after something `goc.engine` imports)
  - [x] MECHANICAL: the same isolation is applied to the OpenClaw tool handler, which shells out with the same `-m` shape and an agent-supplied cwd (`openclaw-plugin/index.ts`)
  - [x] MECHANICAL: the trailing empty `PYTHONPATH` element (`"${PLUGIN_ROOT}:${PYTHONPATH:-}"` with `PYTHONPATH` unset) is removed — it re-adds the cwd a second time
  - [x] MECHANICAL: the engine's own re-invocation (the `quality-pass` title rewrite runs `goc move` in a subprocess) uses the same launcher — found while fixing, not in the original scope
  - [x] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
worker: {who: claude-code, where: host}
---

# The plugin `goc` wrapper lets repo-local Python replace the bundled engine

## Location

`claude-plugin/bin/goc:25` and `codex-plugin/bin/goc:22` — the identical exec
line:

```bash
exec env PYTHONPATH="${PLUGIN_ROOT}:${PYTHONPATH:-}" "$PYTHON" -m goc.cli "$@"
```

`openclaw-plugin/index.ts:644-651` — the same `-m` shape, with a cwd the agent
supplies:

```ts
      const result = await api.runtime.system.runCommandWithTimeout(
        ["python3", "-m", "goc.cli", ...args],
        { cwd, env, timeoutMs: 60_000 },
      );
```

## What's broken

`python -m` prepends the invocation directory to `sys.path` as entry 0. The
plugin root arrives later, via `PYTHONPATH`. So the cwd wins every name
collision, and the collision that matters is the package's own name: a consumer
repo with a top-level `goc/` directory *is* a `goc` package to the interpreter.

Claude Code puts the plugin's `bin/` on the Bash tool's PATH while the plugin is
enabled, and every skill body calls bare `goc`. AGENTS.md describes the intent:

> Claude Code auto-prepends the plugin's `bin/` directory to the Bash tool's
> PATH while the plugin is enabled, so skill bodies keep calling plain
> `goc <verb>` and the wrapper transparently runs the vendored engine.

"Transparently runs the vendored engine" is the claim. What actually runs is
whichever `goc` the working directory offers.

There is a second, smaller copy of the same bug in the one line: with
`PYTHONPATH` unset, `"${PLUGIN_ROOT}:${PYTHONPATH:-}"` expands to
`"<root>:"`, and a trailing empty element means the cwd again. The `-m` entry
is the primary cause — the shadowing still happens with `PYTHONPATH=/nonexistent`
— but the empty element re-adds it and should go too.

## Empirical evidence

After the fix, `reproduce.py` exits 0:

```
[claude-plugin] hijacked=False
  goc, version 0.0.28

[codex-plugin] hijacked=False
  goc, version 0.0.28

[OK] the bundled engine wins over a cwd-local goc/ package.
```

`tests/test_plugin_engine_ignores_working_directory.py` runs every start — both
wrappers, the OpenClaw handler's `gocCommand` (extracted from `index.ts` and run
under node), and `goc.engine._goc_command` — in a scratch cwd holding one impostor at
a time (a `goc/` package, a `dataclasses.py`), and checks that the committed esbuild
output carries the same form. Before the fix both wrappers loaded both impostors and
the other two starts had no launcher form yet; the old handler argv
(`["python3", "-m", "goc.cli", ...]`) loads both impostors the same way, reproduced
against an installed 0.0.28 OpenClaw plugin. Green after the fix, also under
Python 3.10.20.

Before the fix, `uv run python .game-of-cards/deck/plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine/reproduce.py`:

```
[claude-plugin] hijacked=True
  IMPOSTOR-ENGINE
  goc resolved from -> /tmp/goc-shadow-jn4q84oo/goc/__init__.py
  sys.path[:3] = ['/tmp/goc-shadow-jn4q84oo', '.../claude-plugin', '/tmp/goc-shadow-jn4q84oo']

[codex-plugin] hijacked=True
  IMPOSTOR-ENGINE
  goc resolved from -> /tmp/goc-shadow-_4gs08al/goc/__init__.py
  sys.path[:3] = ['/tmp/goc-shadow-_4gs08al', '.../codex-plugin', '/tmp/goc-shadow-_4gs08al']

[FAIL] repo-local goc/ replaces the bundled engine for: claude-plugin, codex-plugin
```

Note the third `sys.path` entry — the cwd a second time, from the trailing
empty `PYTHONPATH` element.

Control: the same wrapper from a cwd without the impostor prints
`goc, version 0.0.27`.

Stdlib-shadowing variant — a `dataclasses.py` at the repo root turns the
takeover into a hard crash before any goc code runs:

```
  File ".../claude-plugin/goc/engine.py", line 26, in <module>
    from dataclasses import dataclass
  File "/tmp/pp-test/dataclasses.py", line 1, in <module>
RuntimeError: shadowed stdlib module from consumer repo cwd
```

## Why it matters

The plugin's marketplace description is "Bundles the goc CLI", and the whole
point of the vendored payload is that a consumer gets a known engine without a
global install. This silently breaks that: the engine a session runs is decided
by the contents of whatever directory the agent happens to be in.

It is also an execution path from repo content to the agent's `goc` command. A
checked-out branch that adds a top-level `goc/` package — deliberately or by
coincidence, since `goc` is a short name — runs its own code every time a skill
invokes a deck verb, with the deck's own file-writing verbs in scope. No
warning, no version mismatch, nothing in the output distinguishes it from the
bundled engine.

Note this repo is itself an instance: running the plugin wrapper from the
`game-of-cards` checkout loads the source tree, not the payload. Here that is
harmless dogfooding, which is part of why it has gone unnoticed.

## Decision

*Resolved 2026-10-25T05:20:07Z:* Option 2: every plugin start and the engine's own re-invocation run goc/_launch.py by absolute path instead of python3 -m goc.cli; the Python 3.10 floor stays

*Reasoning:* It covers the goc-package takeover and the stdlib-shadowing variant on every supported Python without a version branch; the maintainer (Rodja, 2026-10-25) delegated the pick and asked for the fix on main

## Fix

- `goc/_launch.py` (new, mirrored into all three plugin payloads): started by path, its
  first statement replaces `sys.path[0]` (the `goc/` package itself) with the directory
  that holds the package, then `runpy.run_module("goc.cli", run_name="__main__",
  alter_sys=True)` reproduces the `-m` start. The working directory never enters
  `sys.path`.
- `claude-plugin/bin/goc`, `codex-plugin/bin/goc`: `exec env
  PYTHONPATH="${PLUGIN_ROOT}${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON"
  "$PLUGIN_ROOT/goc/_launch.py" "$@"` — no `-m`, no trailing empty element. `PYTHONPATH`
  stays, because commands that `goc attest` runs may rely on it.
- `openclaw-plugin/index.ts`: the handler builds its argv with the top-level
  `gocCommand(args)` (`["python3", <plugin>/goc/_launch.py, ...args]`); `dist/` rebuilt
  with `npm run build` (diff limited to this change).
- `goc/engine.py`: `_goc_command()` for the `goc move` subprocess in
  `_apply_verdict_interactive`.
- Docs and guidance that described the `-m` start: `AGENTS.md`, `goc.md`,
  `openclaw-plugin/README.md`, the `codex-kickoff` skill (template and mirrors), and the
  `_is_plugin_context` docstring.

