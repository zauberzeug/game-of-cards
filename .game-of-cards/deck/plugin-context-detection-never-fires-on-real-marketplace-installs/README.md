---
title: plugin-context-detection-never-fires-on-real-marketplace-installs
summary: "`_is_plugin_context()` detects the bundled-engine context by checking the package's parent dir is literally named `claude-plugin`/`codex-plugin`/`openclaw-plugin` — true only in this source repo. Real marketplace installs put the payload under a version dir, so the `--local-skills` refusal is dead in production and the engine crashes with a raw FileNotFoundError (the payload omits templates/skills/). The OpenClaw no-harness install default is equally dead."
status: open
stage: null
contribution: high
created: "2026-06-12T05:40:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: detection mechanism chosen (Decision required below) and recorded in log.md.
  - [ ] TDD: reproduce.py exits zero inverted — the marketplace-layout install prints the _LOCAL_SKILLS_PLUGIN_REFUSAL (exit 2), not a FileNotFoundError traceback.
  - [ ] TDD: regression test stages the bundled engine under a `<mkt>/game-of-cards/<version>/goc` path (not the source-repo `claude-plugin/goc` path) and asserts the refusal fires; same for the OpenClaw no-harness default.
  - [ ] MECHANICAL: existing tests that fabricate `_plugin/claude-plugin` layouts updated to also cover the versioned layout.
  - [ ] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green).
---

# Plugin-context detection never fires on real marketplace installs

`_is_plugin_context()` and `_is_openclaw_plugin_context()` detect "running
from a plugin payload" by checking whether the parent directory of the
`goc/` package is literally named `claude-plugin` / `codex-plugin` /
`openclaw-plugin`. That is only true in this source repo's checkout. On
every real marketplace install the payload root is a version directory
(e.g. `0.0.24`), so the detection always returns False — the
`--local-skills` refusal is dead code in production, and because the
bundled payload deliberately omits `templates/skills/`, the engine crashes
with a raw `FileNotFoundError` traceback instead.

## Location

- `goc/install.py:484` — `return _PACKAGE_DIR.parent.name in {"claude-plugin", "codex-plugin", "openclaw-plugin"}`
- `goc/install.py:498` — `return _PACKAGE_DIR.parent.name == "openclaw-plugin"`
- `goc/engine.py:4083-4087` — `_claude_plugin_present()` documents the real layouts
- `tests/test_install.py:1891` — test fabricates `cwd / "_plugin" / "claude-plugin"`, the one layout that matches

## What's broken

The detection:

```python
return _PACKAGE_DIR.parent.name in {"claude-plugin", "codex-plugin", "openclaw-plugin"}
```

But the engine's own sibling function `_claude_plugin_present()` documents
the layouts "verified against live Claude Code installs":

```
<root>/cache-or-data/<mkt>/game-of-cards*/<ver>/skills/ (modern versioned)
```

i.e. on a consumer host the parent of the bundled `goc/` package is named
`game-of-cards` or a version string like `0.0.24` — never `claude-plugin`.
The Codex bootstrap finder (`goc/install.py:1100`) greps the same
`.../cache/*/game-of-cards/*/skills/...` shape. AGENTS.md documents the
omission of `templates/skills/` from the payload as safe *because* of the
refusal:

> the bundled engine refuses `--local-skills` on `goc install` and
> `--keep-local-skills` on `goc upgrade` (see `_is_plugin_context` in
> `goc/install.py`), so the skill templates are never read from inside
> the plugin payload.

With the detection dead, that safety story is false on every real install.
The OpenClaw no-harness default (`_is_openclaw_plugin_context`, used at
`install.py:1422` and `install.py:1585`) is equally dead — real OpenClaw
installs fall back to the Claude-harness default the docstring says must
never happen (the closed card
[openclaw-kickoff-defaults-to-claude-install](../openclaw-kickoff-defaults-to-claude-install/)
fixed that default *conditional on this detection working*).

The regression suite stays green because `tests/test_install.py:1891`
constructs `plugin_root = cwd / "_plugin" / "claude-plugin"` — exactly the
one directory name the detection matches, and exactly the layout no
consumer ever has.

## Empirical evidence

`uv run python .game-of-cards/deck/plugin-context-detection-never-fires-on-real-marketplace-installs/reproduce.py`:

```
[marketplace layout 0.0.24/goc]   exit=1
  last stderr line: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/goc-plugin-ctx-d97vcd4u/cache/mkt/game-of-cards/0.0.24/goc/templates/skills'
[source layout claude-plugin/goc] exit=2
  first stderr line: ERROR: --local-skills is not supported when running under the plugin.

DEFECT CONFIRMED: refusal is dead on the real marketplace layout (raw FileNotFoundError traceback instead); it only fires when the payload dir is literally named 'claude-plugin'.
```

## Why it matters

Reachability: any consumer who installed the Claude or Codex plugin via
marketplace and runs `goc install --local-skills` (the documented
vendored-skills path for CI). The wrapper `claude-plugin/bin/goc` sets
`PYTHONPATH` to the cache payload path, so `python3 -m goc.cli` resolves to
the bundled engine whose parent dir is the version string. Instead of the
designed actionable refusal ("install via pipx instead"), the user gets an
unhandled traceback. On OpenClaw, every real install plans the
Claude-harness scaffold (`CLAUDE.md` append, `.claude/` tree) that the
no-harness default was built to prevent.

## Decision required

The defect is determined; the detection mechanism has credible
alternatives:

1. **Capability probe** — detect "bundled payload" by what makes it
   special: `not (_PACKAGE_DIR / "templates" / "skills").exists()`. Zero
   coordination with the sync script; directly tests the condition the
   refusal guards. But conflates "plugin payload" with any broken/partial
   install, and gives no signal for the OpenClaw-vs-Claude distinction.
2. **Sentinel file** — `scripts/sync_plugin_assets.py` writes a
   `goc/_plugin_host` marker (content: `claude` / `codex` / `openclaw`)
   into each payload's `goc/` copy; `_is_plugin_context()` reads it.
   Explicit, distinguishes hosts (keeps `_is_openclaw_plugin_context`
   honest), testable. Requires touching the sync script + porter and the
   wheel must NOT carry the sentinel.
3. **Path-shape heuristic** — extend the name check to also accept
   ancestor names (`game-of-cards*` parent two levels up, version-string
   parent). Smallest diff, but inherits the fragility that caused this
   defect (layouts change; `_claude_plugin_present` already grew four
   accepted shapes).

Option 2 looks most robust (single writer, explicit host signal), with
option 1 as a belt-and-suspenders guard at the skills-read site. A human
should pick.
