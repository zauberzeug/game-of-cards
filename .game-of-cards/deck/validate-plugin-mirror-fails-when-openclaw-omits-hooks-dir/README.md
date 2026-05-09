---
title: validate-plugin-mirror-fails-when-openclaw-omits-hooks-dir
summary: "`uv run goc validate` reports `plugin mirror drift: goc vs openclaw-plugin/goc: templates/hooks (only in goc)` at HEAD. Commit `8277962` (\"Derive Claude hook manifest from templates/hooks/*.py\") added new hook scripts under `goc/templates/hooks/` and `claude-plugin/goc/templates/hooks/`, but did not create a corresponding `openclaw-plugin/goc/templates/hooks/` directory. The OpenClaw plugin intentionally omits the Python hooks (it reimplements them in TS in `index.ts`), and `validate_plugin_mirror_parity()` builds an exclude set of individual hook *files* (`templates/hooks/<name>.py`). Because the entire `templates/hooks/` directory is missing on the OpenClaw side, the comparison reports the parent dir as left-only before recursing into the per-file excludes, so validate fails."
status: active
stage: null
contribution: low
created: 2026-05-09
closed_at: null
human_gate: none
advances:
  - llms-txt-still-recommends-uv-tool-install-as-preferred
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] `uv run goc validate` exits 0 on a clean checkout of `main`
  - [ ] The fix preserves the documented intent (OpenClaw plugin's bundled engine omits `templates/hooks/*.py` because hooks are reimplemented in TS) — i.e. no Python hook scripts are added to `openclaw-plugin/goc/templates/hooks/`
  - [ ] `python scripts/sync_plugin_assets.py --check` continues to pass
worker: {who: "claude[bot]", where: main}
---

# `goc validate` fails when OpenClaw plugin omits hooks dir

## What's wrong

At HEAD (after commit `8277962`), `uv run goc validate` errors:

```
ERROR: plugin mirror drift: goc vs openclaw-plugin/goc: templates/hooks (only in goc)
```

The OpenClaw plugin's bundled engine intentionally does not ship the
Python hook scripts under `goc/templates/hooks/` because it
reimplements each deck hook in TypeScript inside
`openclaw-plugin/index.ts` (per the comment block in
`validate_plugin_mirror_parity()` at `goc/engine.py:599-601`).

The validator builds its exclude set per-file:

```python
openclaw_goc_excludes = claude_goc_excludes | frozenset(
    f"templates/hooks/{name}" for name in hook_names
)
```

That covers files inside the directory, but `_walk()`'s left-only
check at the parent level (`templates/`) sees `hooks` as a directory
that exists on the source side but not on the OpenClaw mirror, and
reports it as `templates/hooks (only in goc)` before the per-file
excludes ever get a chance to apply.

## Why this is gate=none

The intent is documented (OpenClaw reimplements hooks in TS, no
Python files mirrored). The fix is a small change to the validator
to also exclude the directory itself, not just its contents.

## Suggested fix

In `goc/engine.py`, extend `openclaw_goc_excludes` to include the
directory itself in addition to the per-file excludes:

```python
openclaw_goc_excludes = claude_goc_excludes | {"templates/hooks"} | frozenset(
    f"templates/hooks/{name}" for name in hook_names
)
```

`_is_inside_exclude` already short-circuits on a path that equals
an excluded path or sits under one, so the directory entry will
match before the recursion is attempted.

The same fix needs to mirror through to `claude-plugin/goc/engine.py`
and `openclaw-plugin/goc/engine.py` via
`scripts/sync_plugin_assets.py` (which auto-syncs the engine).

## Cross-references

- Commit `8277962` — added the new hook scripts; introduced the drift
- `goc/engine.py:581-680` — `validate_plugin_mirror_parity()`
- `llms-txt-still-recommends-uv-tool-install-as-preferred` — blocked
  on this card because its DoD requires `goc validate` to pass
