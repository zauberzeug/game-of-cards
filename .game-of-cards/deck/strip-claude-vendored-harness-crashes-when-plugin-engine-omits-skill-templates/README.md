---
title: strip-claude-vendored-harness-crashes-when-plugin-engine-omits-skill-templates
status: done
stage: null
contribution: medium
created: "2026-06-22T14:36:14Z"
closed_at: "2026-06-22T14:40:33Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
summary: |
  `_strip_claude_vendored_harness` iterates `templates/skills`
  unconditionally, but the bundled plugin engine omits that subdir.
  Confirming the documented vendored->plugin migration cleanup from a
  plugin-bundled engine therefore raises FileNotFoundError before any
  cleanup runs.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (cleanup completes without crash, user skill preserved)
  - [x] TDD: regression test in tests/ covers the templates/skills-absent cleanup path
  - [x] MECHANICAL: `skills_src.iterdir()` is guarded so an absent template skill tree yields an empty goc-owned set rather than a crash
  - [x] PROCESS: full suite green (`uv run python -m unittest discover -s tests`)
worker: {who: "claude[bot]", where: main}
---

# strip-claude-vendored-harness-crashes-when-plugin-engine-omits-skill-templates

## Location

`goc/install.py:786-790` — inside `_strip_claude_vendored_harness`.

## What's broken

The vendored→plugin migration cleanup builds the set of GoC-owned skill
directory names by iterating the engine's template skill tree
unconditionally:

```python
skills_src = templates / "skills"
goc_owned = {
    p.name for p in skills_src.iterdir()
    if p.is_dir() and skill_for_agent(p.name, "claude")
}
```

But the bundled plugin engine **deliberately omits** `templates/skills/`
— `claude-plugin/goc/templates/` contains `agents/`, `bootstrap/`,
`game_of_cards/`, `hooks/`, and the briefing markdown, but no `skills/`
subdir (the bundled engine refuses `--local-skills`, so it never reads
skill templates). When `skills_src` does not exist, `skills_src.iterdir()`
raises `FileNotFoundError`.

This cleanup is reached from `_apply_upgrade` at `goc/install.py:1685-1695`:

```python
if needs_vendored_cleanup:
    print("This repo is configured for plugin-mode skills ...")
    confirmed = _confirm("Remove leftover vendored layout?", default=False)
    if confirmed:
        _strip_claude_vendored_harness(target, templates)
```

`needs_vendored_cleanup` is gated on `skills_source == plugin` plus a
leftover `.claude/skills/` — **not** on plugin-context detection. So it
fires during exactly the flow AGENTS.md documents for moving a vendored
repo to plugin mode: "edit `skills_source: plugin` in
`.game-of-cards/config.yaml`, then `goc upgrade` — which detects the
leftover `.claude/skills/` and prompts for cleanup." Confirming the
prompt under a plugin-bundled engine crashes before any file is removed.

## Why it matters

This is the documented migration path for plugin adopters, and it is run
from the plugin-bundled engine (the engine a plugin user has on hand).
The crash aborts the cleanup entirely: the leftover vendored skills stay,
`goc validate` keeps skipping the parity check (plugin mode) while stale
vendored skills linger, and the user sees a raw traceback instead of a
completed migration.

This is distinct from `plugin-context-detection-never-fires-on-real-marketplace-installs`,
which addresses install/upgrade *detection* sites (install.py:484/498):
this cleanup path is reachable in a *correctly-detected* plugin context
(skills_source is explicitly `plugin`), so fixing detection does not fix
this crash. install.py:788 is absent from that card's location list.

## Empirical evidence

`reproduce.py` copies the real template tree minus `skills/` (the plugin
payload shape) and runs the cleanup against a repo with one GoC-managed
and one user-authored leftover skill.

Before the fix, the cleanup crashed:

```
REPRODUCED: FileNotFoundError during cleanup: [Errno 2] No such file or directory: '.../templates/skills'
Cleanup crashed; vendored->plugin migration is broken from the plugin engine.
exit=1
```

After guarding `skills_src.iterdir()` with `skills_src.is_dir()`:

```
OK: cleanup completed without crash; user-authored skill preserved
  my-custom-skill still present: True
exit=0
```

The regression test
`tests/test_install.py::ClaudeHarnessInstallTest::test_strip_vendored_harness_survives_absent_template_skill_tree`
exercises the same path and was verified to fail (FileNotFoundError)
without the guard.

## Fix

Guard the iteration so an absent template skill tree yields an empty
GoC-owned set instead of crashing. When the template skill tree is
absent (plugin payload), GoC-owned skill *names* cannot be identified
from templates, so the conservative behavior is to skip skill-dir
removal — never destroy authored content — and let the hook-file and
settings-entry removal proceed:

```python
skills_src = templates / "skills"
goc_owned = {
    p.name for p in skills_src.iterdir()
    if p.is_dir() and skill_for_agent(p.name, "claude")
} if skills_src.is_dir() else set()
```

No design decision: with no template source the set is empty, no skill
dir matches, none are removed, and the remaining cleanup (hook files,
`.claude/settings.json` GoC entries) runs as before.
