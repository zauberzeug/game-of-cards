---
title: plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove
summary: "Run through the Claude Code plugin's bundled engine (what a bare goc runs inside a Claude Code session with the plugin enabled), the vendored-to-plugin cleanup promises to remove GoC-managed skill directories, then removes hooks and settings entries but keeps all 16 GoC skill dirs. The bundled engine omits templates/skills/, the only source the cleanup reads GoC's skill names from, yet the payload's own skills/ directory holds exactly that set. goc.md now has to tell users to run the switch with the standalone goc instead."
status: open
stage: null
contribution: medium
created: "2026-10-02T04:45:41Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — the documented switch (`skills_source: plugin`, then `goc upgrade` answering `y`) run through `claude-plugin/bin/goc` on a scratch `--local-skills` repo leaves no GoC skill dir and keeps a repo-owned skill
  - [ ] TDD: a regression test in `tests/test_install.py` runs `_strip_claude_vendored_harness` from a plugin-shaped package (no `templates/skills/`, a sibling `skills/`) and asserts GoC-named dirs go and other dirs stay
  - [ ] MECHANICAL: when no source of GoC skill names is available, the prompt says it will leave the skill directories rather than promising to remove them
  - [ ] MECHANICAL: `goc.md` § "Coexistence with the repo-local harness" drops its standalone-`goc` caveat; `tests/test_plugin_switch_recipe.py::test_bundled_engine_caveat_matches_its_cleanup` fails until it does
  - [ ] PROCESS: `uv run python -m unittest discover -s tests`, `uv run goc validate` and `python scripts/sync_plugin_assets.py --check` pass
---

# The plugin engine's cleanup keeps every GoC skill dir its prompt promises to remove

## Location

`goc/install.py`, `_strip_claude_vendored_harness`:

```python
            skills_src = templates / "skills"
            # The bundled plugin engine omits templates/skills/, so the set of
            # GoC-owned skill names cannot be derived there. Skip skill-dir
            # removal in that case (never destroy authored content) and let the
            # hook-file and settings-entry cleanup below proceed.
            goc_owned = {
                p.name for p in skills_src.iterdir()
                if p.is_dir() and skill_for_agent(p.name, "claude")
            } if skills_src.is_dir() else set()
```

The prompt `upgrade()` prints right before calling it:

```
Cleanup removes GoC-managed skill directories, GoC hook files, and
GoC entries in .claude/settings.json. Non-GoC skills in .claude/skills/
are preserved.
```

## What's broken

The plugin payload omits `templates/skills/` by design (`AGENTS.md`
§ "Plugin assets are auto-synced"). Run from the payload, the cleanup's
GoC-owned set is therefore empty and no skill dir is removed. The prompt
promises otherwise, nothing is printed afterwards, and the run reports
"goc upgrade complete".

The comment's premise ("the set of GoC-owned skill names cannot be
derived there") does not hold for the Claude payload. Its own `skills/`
directory, a sibling of the bundled `goc/` package, is a byte copy of the
Claude-filtered skill templates. Measured on 2026-10-02, the dir names of
`claude-plugin/skills/` equal
`{n for n in goc/templates/skills if skill_for_agent(n, "claude")}`
exactly. The Codex and OpenClaw payloads differ by their kickoff complement
(`codex-kickoff` / `openclaw-kickoff` in place of `claude-kickoff`).

This is the engine a Claude Code user reaches by default. With the plugin
enabled, its `bin/` sits first on the Bash tool's PATH, so asking the
agent to "upgrade goc" (`Skill(upgrade)`) runs the bundled copy.

## Empirical evidence

Scratch `goc install --local-skills` repo (source engine), then
`skills_source: plugin` and `echo y | claude-plugin/bin/goc upgrade`:

```
This repo is configured for plugin-mode skills (skills_source: plugin)
but a leftover .claude/skills/ from a prior vendored install was found.
Cleanup removes GoC-managed skill directories, GoC hook files, and
GoC entries in .claude/settings.json. Non-GoC skills in .claude/skills/
are preserved.
goc upgrade complete for agents: claude — 0.0.27.post1.dev465 → 0.0.27.
```

Afterwards `.claude/hooks/`, `_goc-bootstrap.sh` and the settings entries
are gone, but `.claude/skills/` still holds all 16 GoC skill dirs next to
the repo's own `my-own-skill`. `reproduce.py` runs the same switch through
the wrapper:

```
bundled-engine upgrade exit=0; prompt promised skill-dir removal=True
GoC skill dirs left: 16 of 16 ['advance-card', 'audit-deck', 'card-schema', 'claude-kickoff', 'create-card', 'decide-card', 'deck', 'finish-card', 'kickoff', 'next-card', 'pull-card', 'refine-deck', 'retrospective', 'scan-deck', 'standup', 'upgrade']
repo's own skill kept: True; .claude/hooks/ left: False

FAIL: the bundled engine's cleanup kept GoC's skill dirs (or lost the repo's own skill).
```

`tests/test_plugin_switch_recipe.py::test_bundled_engine_caveat_matches_its_cleanup`
runs the same switch on every CI run and records the behavior today.

## Why it matters

The vendored copies stay checked in, and nothing refreshes them, so they
drift from the plugin's. They shadow nothing only because the plugin's
skills win on a name clash. Every reader who follows the switch through
the agent ends up half-migrated without being told. `goc.md` (fixed by
[cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it](../cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it/))
now tells readers to run the switch with the standalone `goc`. That is
the workaround, and it is the sentence this card retires.

## Fix

When `templates/skills/` is absent and `_is_plugin_context()` holds, read
the GoC-owned names from the payload's own `skills/`
(`_PACKAGE_DIR.parent / "skills"`), still filtered through
`skill_for_agent(name, "claude")`. Under the Claude payload that is the
exact set. Under the Codex and OpenClaw payloads it misses only
`claude-kickoff`, which is no worse than today. If neither source exists,
keep skipping skill-dir removal (never destroy authored content), and
change the prompt to say so instead of promising removal.

A generated name manifest shipped inside the package would also work, but
it adds a new synced artifact to maintain for data the payload already
carries. Prior-version names are out of scope and belong to
[goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/).
Adjacent but distinct:
[plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos](../plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos/)
covers the same engine *before* the pin is switched. Whichever behavior
that card picks, a repo it sends to `skills_source: plugin` lands here.
