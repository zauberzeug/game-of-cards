---
title: plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine
summary: "The plugin bin/goc wrappers invoke \"python3 -m goc.cli\", and -m puts the invocation cwd at sys.path[0] — ahead of the plugin root supplied via PYTHONPATH. Any consumer repo containing a top-level goc/ package silently takes over the goc command in that session, and a repo-root module shadowing a stdlib name the engine imports hard-crashes the wrapper instead. The plugin advertises a bundled engine; what actually runs is decided by repo content."
status: open
stage: null
contribution: high
created: "2026-09-10T04:50:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] DECISION: pick the isolation mechanism given the Python 3.10 floor — `-P` / `PYTHONSAFEPATH` are 3.11+, so either raise the floor, branch on version, or stop using `-m` (see `## Decision required`)
  - [ ] TDD: `reproduce.py` exits zero — a cwd-local `goc/` package no longer replaces the bundled engine for either wrapper
  - [ ] TDD: a regression test covers the stdlib-shadowing variant (a repo-root module named after something `goc.engine` imports)
  - [ ] MECHANICAL: the same isolation is applied to the OpenClaw tool handler, which shells out with the same `-m` shape and an agent-supplied cwd (`openclaw-plugin/index.ts`)
  - [ ] MECHANICAL: the trailing empty `PYTHONPATH` element (`"${PLUGIN_ROOT}:${PYTHONPATH:-}"` with `PYTHONPATH` unset) is removed — it re-adds the cwd a second time
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and `uv run goc validate` pass
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

`uv run python .game-of-cards/deck/plugin-goc-wrapper-lets-repo-local-python-replace-the-bundled-engine/reproduce.py`:

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

## Decision required

The clean fixes are version-gated, and `pyproject.toml` supports Python 3.10:

1. **`-P` / `PYTHONSAFEPATH=1`** — exactly this problem's fix, but both are
   **3.11+**. Requires either raising the floor to 3.11 (a consumer-visible
   break; AGENTS.md and the plugin READMEs all state "Python 3.10+ is the only
   host prerequisite") or branching in the wrapper on the interpreter version,
   which leaves 3.10 hosts unprotected.
2. **Stop using `-m`** — invoke a small launcher inside the payload by absolute
   path, which makes `sys.path[0]` the payload directory instead of the cwd.
   Works on 3.10, but changes how the entry point is reached and needs care so
   `goc.cli`'s own imports still resolve against the payload.
3. **Sanitize inside the entry point** — have `goc/cli.py` drop a `sys.path[0]`
   that is not the payload root before importing the engine. Works on 3.10, but
   it is too late for the stdlib-shadowing variant, which fails at
   `goc.engine` import time.

Options 2 and 3 differ in whether protection covers the stdlib case; option 1
differs in supported-host policy. That is a maintainer call.

Whatever is picked also applies to the OpenClaw handler, which has the same
shape with a less predictable cwd.
