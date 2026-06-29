---
title: skills-source-auto-resolves-vendored-when-claude-plugin-root-names-a-versioned-payload
status: done
stage: null
contribution: medium
created: "2026-06-29T02:39:33Z"
closed_at: "2026-06-29T02:44:44Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] `_claude_plugin_present()` returns True when `CLAUDE_PLUGIN_ROOT` points at a payload root whose `skills/` subtree exists, regardless of the root's basename.
  - [x] The `~/.claude/plugins` container candidate still requires a `game-of-cards*` payload (no new false positive from a non-GoC `skills/` dir there).
  - [x] Regression test added covering `CLAUDE_PLUGIN_ROOT` pointing at a versioned payload root (e.g. `.../game-of-cards/0.0.25`).
  - [x] `reproduce.py` prints PASS after the fix.
  - [x] `uv run goc validate` passes and the full regression suite stays green.
worker: {who: "claude[bot]", where: main}
---

# `skills_source: auto` resolves to `vendored` when `CLAUDE_PLUGIN_ROOT` names a versioned payload

## Problem

`_claude_plugin_present()` in `goc/engine.py` resolves `skills_source: auto`
by checking whether a Claude Code GoC plugin payload is present. Its
documented "layout 1" (docstring at `goc/engine.py:4520`) is:

```
<root>/skills/   (root is the payload, e.g. CLAUDE_PLUGIN_ROOT)
```

But the fast-path that implements it (`goc/engine.py:4541`) additionally
requires the root's basename to start with `game-of-cards`:

```python
if (root / "skills").is_dir() and root.name.startswith("game-of-cards"):
    return True
```

On a real marketplace install, Claude Code sets `CLAUDE_PLUGIN_ROOT` to a
**versioned** payload root — e.g. `.../game-of-cards/0.0.25` — whose
basename is the version (`0.0.25`), not `game-of-cards`. So the name guard
fails, the fast-path is skipped, and the `rglob("game-of-cards*")` fallback
(`goc/engine.py:4544`) only descends *into* `CLAUDE_PLUGIN_ROOT` looking for
a `game-of-cards*` directory — but here the `game-of-cards` segment is an
**ancestor** of the env root, never a descendant, so it is never matched.
`_claude_plugin_present()` returns `False` and `effective_skills_source()`
(`goc/engine.py:4560`) falls back to `vendored`.

The code contradicts its own docstring's layout-1 claim.

## Why it matters

`CLAUDE_PLUGIN_ROOT` is the authoritative pointer to the running plugin's
payload — Claude Code sets it only for the GoC plugin's own root. When a
repo is configured `skills_source: auto` and the plugin is the *actual*
source of skills, `goc upgrade` calls `effective_skills_source()` to pin
the resolved mode (`goc/install.py:1713-1718`) and writes
`skills_source: vendored` — the wrong mode. `goc validate` then enforces
vendored skill-dir parity (`validate_skill_dir_parity`) and fires a
spurious "missing skills" error in a repo that is genuinely plugin-mode and
has no `.claude/skills/` checked in.

Reachability path: a marketplace plugin install (no `~/.claude/plugins`
copy, or one that does not mask the bug) + a legacy/auto `skills_source`
repo running `goc upgrade` or `goc validate`. The sibling card
`plugin-auto-detection-misses-versioned-marketplace-paths` (done) fixed the
`~/.claude/plugins` *container* candidate by adding the `rglob` descent, but
its `reproduce.py` explicitly pops `CLAUDE_PLUGIN_ROOT` — so the env-root
fast-path was never exercised and this gap is previously undocumented.

## Reproduction

`reproduce.py` constructs a versioned payload root, points
`CLAUDE_PLUGIN_ROOT` at it (with `HOME` set to an empty dir so the
`~/.claude/plugins` candidate cannot mask the bug), and asserts detection.

Before the fix:

```
payload root basename     : 0.0.25
payload/skills exists      : True
_claude_plugin_present()   : False   <-- BUG (should be True)
effective_skills_source()  : vendored  <-- wrong (should be plugin)
FAIL
```

## Proposed fix

Drop the basename guard for the `CLAUDE_PLUGIN_ROOT` candidate only:
`CLAUDE_PLUGIN_ROOT/skills/` existing is sufficient proof of presence
regardless of the root's name. Keep the `game-of-cards*` requirement for
the `~/.claude/plugins` container candidate (which is a directory of many
plugins, not a payload root) so no non-GoC `skills/` dir there can produce
a false positive. The `rglob` fallback stays for both candidates.
