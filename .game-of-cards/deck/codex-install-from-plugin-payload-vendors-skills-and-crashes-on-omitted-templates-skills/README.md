---
title: codex-install-from-plugin-payload-vendors-skills-and-crashes-on-omitted-templates-skills
status: open
stage: null
contribution: high
created: "2026-06-24T08:18:30Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: `reproduce.py` drives a Codex `install`/`upgrade` with the
        module globals set to a plugin-payload root (so `_is_plugin_context()`
        is True) and shows whether the skill-tree walk raises `FileNotFoundError`
        on the omitted `templates/skills` dir. Exits 1 if it crashes, 0 if a
        clean refusal/no-op is produced.
  - [ ] DECISION: pick the intended behavior — refuse (mirror
        `_LOCAL_SKILLS_PLUGIN_REFUSAL`), silently no-op the skill vendoring,
        or make Codex-from-plugin unreachable — and record the choice + why.
  - [ ] MECHANICAL: implement the chosen guard so the plugin-context Codex path
        no longer reaches an `.iterdir()` on a non-existent directory.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` and
        `uv run goc validate` pass.
---

# Codex install/upgrade from a plugin payload vendors skills and may crash on the omitted `templates/skills`

> ⚠ UNVERIFIED — code-shape confirmed, runtime reachability not yet proven by a
> `reproduce.py`. See "Falsification" below before promoting.

## Hypothesis

The plugin-context refusal only guards the `--local-skills` flag
(`goc/install.py:1438`):

```python
if local_skills and _is_plugin_context():
    print(_LOCAL_SKILLS_PLUGIN_REFUSAL, file=sys.stderr)
    sys.exit(2)
```

But Codex *always* vendors skills regardless of any flag
(`goc/install.py:530-536`):

```python
def _should_use_local_skills(agent: str, *, local_skills: bool) -> bool:
    # Codex always uses vendored layout (no plugin yet).
    return agent != "claude" or local_skills
```

So a Codex `install`/`upgrade` reaches the skill-tree walk, which
`.iterdir()`s `templates/skills` — a directory the plugin payloads
(`claude-plugin/goc/`, `codex-plugin/goc/`, `openclaw-plugin/goc/`)
deliberately omit (the sync excludes `templates/skills` from the engine
deep-mirror; verified `ls .../goc/templates/skills` → "No such file or
directory"). The walk has no `.exists()` guard at `_iter_skill_assets`
/ `_sync_skill_tree`, so the hypothesis is an unhandled
`FileNotFoundError`. The Claude `--local-skills` path is correctly
refused; Codex's unconditional vendoring slips past the guard's
`local_skills and ...` condition.

## Why it matters

If reachable, a Codex install/upgrade run from inside a bundled plugin
engine crashes with an uncaught traceback after partial work, rather
than refusing cleanly the way the Claude path does. High contribution
because it would break the documented Codex-plugin install/upgrade flow
entirely under the plugin runtime.

## Distinct from existing cards

- `codex-only-install-pins-skills-source-to-plugin-skipping-parity-check`
  — about `skills_source` pinning, not the missing-dir crash.
- `plugin-context-detection-never-fires-on-real-marketplace-installs`
  — about detection *failing* to fire. Here the hypothesis is that
  detection *does* fire but the guard's condition is too narrow.

## Why deferred / why gated

`unverified`: the code shape is confirmed, but I have not proven that
`_is_plugin_context()` actually returns True in a real Codex-plugin
runtime, nor that a Codex plugin install ever invokes `goc install` /
`goc upgrade` (Codex plugins may not run the vendoring path at all). If
the path is unreachable in practice this is a latent guard gap, not a
live crash — which changes both severity and the right fix.

`human_gate: decision`: even once reachability is confirmed, the fix is
a design call (refuse vs. silent no-op vs. unreachable-by-construction)
that should be decided, not assumed.

## Falsification

1. Set `goc.install` / `goc.engine` module globals to a `codex-plugin/`
   payload root so `_is_plugin_context()` is True; `chdir` to a fresh
   temp repo; call the Codex install path. Assert whether the skill-tree
   walk raises `FileNotFoundError` on `templates/skills`.
2. If it does not crash (e.g. an earlier guard short-circuits, or the
   real Codex plugin never calls install), disprove and record where the
   path actually terminates.

Surfaced by a general-purpose install.py hunter during an empty-queue
audit-deck pass.
