---
title: plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove
summary: "Run through the Claude Code plugin's bundled engine (what a bare goc runs inside a Claude Code session with the plugin enabled), the vendored-to-plugin cleanup promised to remove GoC-managed skill directories, then kept all 16, because the payload omits templates/skills/, the only place the cleanup read GoC's skill names from. A new _goc_skill_names helper now falls back to the payload's own skills/ tree beside the bundled goc/. It keys on that tree rather than on _is_plugin_context(), so versioned marketplace installs are covered too. The prompt promises skill-dir removal only when the cleanup can do it, and goc.md no longer tells readers to run the switch with the standalone goc."
status: done
stage: null
contribution: medium
created: "2026-10-02T04:45:41Z"
closed_at: "2026-10-15T04:39:53Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — the documented switch (`skills_source: plugin`, then `goc upgrade` answering `y`) run through `claude-plugin/bin/goc` on a scratch `--local-skills` repo leaves no GoC skill dir and keeps a repo-owned skill
  - [x] TDD: a regression test in `tests/test_install.py` runs `_strip_claude_vendored_harness` from a plugin-shaped package (no `templates/skills/`, a sibling `skills/`) and asserts GoC-named dirs go and other dirs stay
  - [x] MECHANICAL: when no source of GoC skill names is available, the prompt says it will leave the skill directories rather than promising to remove them
  - [x] MECHANICAL: `goc.md` § "Coexistence with the repo-local harness" drops its standalone-`goc` caveat; `tests/test_plugin_switch_recipe.py::test_bundled_engine_caveat_matches_its_cleanup` fails until it does
  - [x] PROCESS: `uv run python -m unittest discover -s tests`, `uv run goc validate` and `python scripts/sync_plugin_assets.py --check` pass
worker: {who: "claude[bot]", where: main}
---

# The plugin engine's cleanup keeps every GoC skill dir its prompt promises to remove

## Location

`goc/install.py`, `_strip_claude_vendored_harness`, before the fix:

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

## What was broken

The plugin payload omits `templates/skills/` by design (`AGENTS.md`
§ "Plugin assets are auto-synced"). Run from the payload, the cleanup's
GoC-owned set was therefore empty and no skill dir was removed. The prompt
promised otherwise, nothing was printed afterwards, and the run reported
"goc upgrade complete".

The comment's premise ("the set of GoC-owned skill names cannot be
derived there") did not hold for the Claude payload. Its own `skills/`
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

Measured on 2026-10-02 in a scratch `goc install --local-skills` repo
(source engine), with `skills_source: plugin` set, then
`echo y | claude-plugin/bin/goc upgrade`:

```
This repo is configured for plugin-mode skills (skills_source: plugin)
but a leftover .claude/skills/ from a prior vendored install was found.
Cleanup removes GoC-managed skill directories, GoC hook files, and
GoC entries in .claude/settings.json. Non-GoC skills in .claude/skills/
are preserved.
goc upgrade complete for agents: claude — 0.0.27.post1.dev465 → 0.0.27.
```

Afterwards `.claude/hooks/`, `_goc-bootstrap.sh` and the settings entries
were gone, but `.claude/skills/` still held all 16 GoC skill dirs next to
the repo's own `my-own-skill`. `reproduce.py` runs the same switch through
the wrapper. Before the fix:

```
bundled-engine upgrade exit=0; prompt promised skill-dir removal=True
GoC skill dirs left: 16 of 16 ['advance-card', 'audit-deck', 'card-schema', 'claude-kickoff', 'create-card', 'decide-card', 'deck', 'finish-card', 'kickoff', 'next-card', 'pull-card', 'refine-deck', 'retrospective', 'scan-deck', 'standup', 'upgrade']
repo's own skill kept: True; .claude/hooks/ left: False

FAIL: the bundled engine's cleanup kept GoC's skill dirs (or lost the repo's own skill).
```

After the fix (2026-10-15):

```
bundled-engine upgrade exit=0; prompt promised skill-dir removal=True
GoC skill dirs left: 0 of 16 []
repo's own skill kept: True; .claude/hooks/ left: False

OK: the bundled engine's cleanup removed GoC's skill dirs and kept the repo's own.
```

`tests/test_plugin_switch_recipe.py::test_bundled_engine_caveat_matches_its_cleanup`
runs the same switch on every CI run. It failed after the engine fix until
`goc.md` dropped its caveat, and it fails again if the bundled engine ever
leaves the dirs behind while the page stays silent.

## Why it matters

The vendored copies stayed checked in, and nothing refreshed them, so they
drifted from the plugin's. They shadowed nothing only because the plugin's
skills win on a name clash. Every reader who followed the switch through
the agent ended up half-migrated without being told. `goc.md` (fixed by
[cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it](../cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it/))
told readers to run the switch with the standalone `goc`. That was the
workaround, and this card retired it.

## Fix applied

- `goc/install.py` gains `_goc_skill_names(templates, agent)`. It returns
  the names of the skills GoC ships for an agent, or None. It reads
  `templates/skills/` wherever that tree ships (the wheel, the source
  tree). Otherwise it reads the payload's flat `skills/` beside the
  bundled `goc/` (`templates.parent.parent / "skills"`). Only dirs holding
  a `SKILL.md` count, and every name still goes through `skill_for_agent`.
  `_strip_claude_vendored_harness` takes its GoC-owned set from the helper
  and, as before, keeps every skill dir when there is no set.
- The fallback keys on the payload's tree, not on `_is_plugin_context()`
  as the original sketch proposed. That detection tests the payload dir's
  name. The name is `claude-plugin` only in this source tree; a
  marketplace install names the dir after the version. So the sketch would
  have turned `reproduce.py` green and changed nothing on a real install
  ([plugin-context-detection-never-fires-on-real-marketplace-installs](../plugin-context-detection-never-fires-on-real-marketplace-installs/),
  parked at `decision`, now carries a pointer here). A `skills/` tree
  beside the payload's `goc/` is the shape `_claude_plugin_present`
  documents as verified on live installs. Three things stop a stray
  `skills/` next to some other package from costing a user anything. The
  fallback runs only when `templates/skills/` is absent, which never
  happens in a wheel. Only `SKILL.md` dirs count. And nothing is deleted
  until the user answers `y`.
- `upgrade()`'s cleanup prompt asks the same helper. When it has names,
  the wording is unchanged. Without them, the prompt says the cleanup
  removes GoC hook files and settings entries but leaves every skill
  directory in place. It points to a goc from
  `pipx install game-of-cards` for a rerun that removes them too.
- `goc.md` § "Coexistence with the repo-local harness" drops the
  standalone-`goc` caveat and now says any `goc` can run the switch,
  including the bundled engine. `AGENTS.md` § "Plugin assets are
  auto-synced" now says where the bundled engine reads GoC's skill names.
- Tests in `tests/test_install.py`:
  - `test_strip_vendored_harness_reads_goc_skill_names_from_a_plugin_payload`
    stages the package without `templates/skills/` under a
    `plugins/cache/mkt/game-of-cards/0.0.28/` root, with the Claude skill
    tree beside it. GoC-named dirs go; the repo's own skill stays, and so
    does a payload dir that has no `SKILL.md`.
  - `test_strip_vendored_harness_survives_absent_template_skill_tree` now
    stages a package with no skill tree at all, in a fixed layout. In its
    old layout, the new fallback would have read a `skills/` dir from the
    system temp root, one level above the test's temp dir.
  - `test_cleanup_prompt_promises_only_the_skill_dir_removal_it_performs`
    runs the documented switch end to end from the source tree, the
    marketplace-shaped payload and the stripped package. It checks the
    prompt's promise against what was actually removed.

  Each of four injected mutations turns at least one of these tests red:
  gating the fallback on `_is_plugin_context()`, removing the fallback,
  dropping the `SKILL.md` filter, and always printing the promise.

One gap remains, accepted by the original sketch. Run from the Codex or
OpenClaw payload, the names lack `claude-kickoff`, because those trees
carry their own kickoff complement, so that one dir stays. Before the
fix, all 16 stayed.

The sketch's alternative, a generated name manifest shipped inside the
package, was not needed: the payload already carries the data, and a
manifest is one more synced artifact to maintain. Prior-version names are
out of scope and belong to
[goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install](../goc-upgrade-cleanup-misses-prior-version-skills-and-hooks-renamed-since-install/).
Adjacent but distinct:
[plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos](../plugin-engine-upgrade-crashes-with-a-traceback-in-vendored-pinned-repos/)
covers the same engine *before* the pin is switched. Whichever behavior
that card picks, a repo it sends to `skills_source: plugin` then runs
this cleanup.
