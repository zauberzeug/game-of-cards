---
title: plugin-and-marketplace-descriptions-still-advertise-uv-as-required
summary: "The Claude Code plugin descriptions in `claude-plugin/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` still claim 'requires uv on host PATH' even though the plugin wrapper switched to `python3 -m goc.cli` in commit 8d64a3f. The bin/goc script and AGENTS.md both document Python 3.10+ as the only host prerequisite — the marketplace-visible descriptions are stale and overstate the install prerequisites users see before installing."
status: done
stage: null
contribution: medium
created: "2026-05-31T01:36:05Z"
closed_at: "2026-05-31T01:38:35Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] MECHANICAL: `claude-plugin/.claude-plugin/plugin.json` description no longer mentions "requires uv on host PATH"; replacement names Python 3.10+ as the prerequisite.
  - [x] MECHANICAL: `.claude-plugin/marketplace.json` plugin description aligned with the same wording.
  - [x] EMPIRICAL: `grep -rn "requires uv" claude-plugin/ .claude-plugin/` returns no hits.
  - [x] PROCESS: `python scripts/sync_plugin_assets.py --check` still passes (these files are not auto-synced — drift guard only covers mirrored payloads).
  - [x] PROCESS: `uv run goc validate` introduces no new errors (deck has pre-existing unrelated errors; verified by comparing validate output with and without these edits — output is identical).
worker: {who: "claude[bot]", where: main}
---

# Plugin and marketplace descriptions still advertise uv as required

## What's broken

`claude-plugin/.claude-plugin/plugin.json:3` reads:

```json
"description": "Game of Cards skills and hooks — agile work-card methodology for Claude Code agents. Bundles the goc CLI; requires uv on host PATH.",
```

`.claude-plugin/marketplace.json:15` reads:

```json
"description": "Game of Cards skills and hooks for Claude Code. Bundles the goc CLI; requires uv on host PATH."
```

Both descriptions are the user-facing copy that surfaces in Claude
Code's plugin browser and marketplace listing — what a prospective
installer reads before deciding whether the prerequisites are
acceptable.

The claim is no longer true. `claude-plugin/bin/goc` invokes the
bundled engine directly:

```bash
exec env PYTHONPATH="${PLUGIN_ROOT}:${PYTHONPATH:-}" "$PYTHON" -m goc.cli "$@"
```

with `$PYTHON` resolved as `python3` (preferred) or `python`. The
wrapper's own header comment ("No venv, no uv, no first-call
latency.") documents the deliberate move away from uv. AGENTS.md
reinforces it: "Python 3.10+ is the only host prerequisite … No
venv, no `uv`, no first-call latency."

## Why it matters

The two strings ship to two public surfaces that goc owns:

- The Claude Code plugin manifest (`plugin.json`) — read by the
  Claude Code runtime and shown in the plugin-management UI.
- The Anthropic Community Marketplace metadata
  (`marketplace.json`) — the listing copy users see before
  installing.

Both turn one false-positive prerequisite into a real user-facing
friction: a prospective installer who reads "requires uv on host
PATH" either installs uv unnecessarily (waste) or skips the plugin
entirely (lost install). Both descriptions were last updated when
the wrapper genuinely shelled out via `uv run` and were not
refreshed by commit `8d64a3f` ("feat: drop uv from plugin wrapper;
python3 -m goc.cli is now the entry point"), which only touched
`bin/goc`, `claude-plugin/README.md`, and `CLAUDE.md`.

Reachability: both files are read directly by the host runtime
(`plugin.json` by Claude Code's plugin loader; `marketplace.json` by
the marketplace's metadata fetch). They are NOT autosynced from any
other source — `scripts/sync_plugin_assets.py` mirrors goc package
contents and skill templates into the plugin payload, but
`plugin.json` and `marketplace.json` are hand-maintained config
files explicitly excluded from auto-sync (see AGENTS.md "Plugin
assets are auto-synced — edit only the template"). So they stay
stale until a human edits them.

## Fix

Replace the trailing "; requires uv on host PATH" clause in both
descriptions with the current prerequisite. Suggested wording
(matching `claude-plugin/bin/goc`'s own diagnostic):

- `claude-plugin/.claude-plugin/plugin.json:3`:
  `"Game of Cards skills and hooks — agile work-card methodology for Claude Code agents. Bundles the goc CLI; requires Python 3.10+ on host PATH."`
- `.claude-plugin/marketplace.json:15`:
  `"Game of Cards skills and hooks for Claude Code. Bundles the goc CLI; requires Python 3.10+ on host PATH."`

Single-line string edits in two files. No structural change; the
version field, name, and the rest of each file stay untouched.
