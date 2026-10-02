---
title: cli-reference-plugin-switch-recipe-deletes-user-skills-and-the-next-upgrade-reverts-it
summary: "goc.md's vendored-to-plugin recipe told the reader to delete .claude/skills/, .claude/hooks/ and the GoC settings entries by hand. That deleted every skill the repo kept there, and because skills_source stayed vendored, the next goc upgrade re-vendored all 16 GoC skills, 3 hook scripts and 3 settings entries (verified by reproduce.py). The section now gives the supported switch (skills_source: plugin, then goc upgrade and accept the cleanup), says what the cleanup preserves, and warns that the plugin's bundled engine leaves GoC's skill dirs behind. goc validate's double-fire remedy carried a second hand-delete copy and was fixed too. tests/test_plugin_switch_recipe.py runs the documented steps against a scratch install."
status: done
stage: null
contribution: high
created: "2026-09-28T01:34:17Z"
closed_at: "2026-10-02T04:50:06Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation, api-contract]
definition_of_done: |
  - [x] TDD: a reproduce.py follows the `goc.md:162` recipe on a scratch `--local-skills` install holding one user-authored skill, then runs `goc upgrade`, and asserts the repo ends in plugin mode with the user skill intact — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] MECHANICAL: `goc.md`'s coexistence section gives the supported switch (`skills_source: plugin` in `.game-of-cards/config.yaml`, then `goc upgrade` and accept the cleanup) instead of a hand-delete of `.claude/skills/`, and says the cleanup preserves non-GoC skills
  - [x] MECHANICAL: drop the `unverified` tag once reproduce.py lands; the correction carries a derive-from-tree guard or is listed on `doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`
  - [x] MECHANICAL: `goc validate`'s `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE` remedy, a second copy of the hand-delete recipe, routes through `goc upgrade`'s cleanup too
worker: {who: "claude[bot]", where: main}
---

# The CLI reference's plugin-switch recipe deletes user skills, and the next upgrade reverts it

> **Verified and fixed 2026-10-02.** Filed as unverified by an audit hunter
> on the docs-vs-code seam on 2026-09-28. `reproduce.py` confirmed both
> failure modes. The section now gives the supported switch, and a guard
> runs that switch against a scratch install.

## What was broken

`goc.md` § "Coexistence with the repo-local harness" told a vendored repo
moving to the Claude Code plugin:

> To clean up a previous repo-local harness installation, remove
> `.claude/skills/`, `.claude/hooks/`, and the GoC hook entries from
> `.claude/settings.json`, then rely on the plugin entirely.

That recipe failed in two ways:

1. **It deleted user content.** Removing `.claude/skills/` wholesale took
   every skill the repo kept there. The engine's own cleanup
   (`_strip_claude_vendored_harness` in `goc/install.py`) deliberately
   keeps those skills.
2. **It did not stick.** The recipe never touched
   `.game-of-cards/config.yaml`, so `skills_source` stayed `vendored`
   (written by `goc install --local-skills`). In `upgrade()`, a `vendored`
   pin puts every agent in `local_skills_agents`, so the next routine
   `goc upgrade` (which `goc.md` § "Upgrade an install" recommends)
   re-vendored all GoC skills, hooks and `settings.json` entries. The hooks
   fired twice again, and nothing warned about it.

The supported switch (set `skills_source: plugin`, then run `goc upgrade`
and accept its cleanup) was documented only in this repo's `AGENTS.md`
§ "`skills_source` — which install path owns `.claude/skills/`". No
consumer reads that file. The recipe predated the key: it was written on
2026-05-05, and `skills_source` arrived on 2026-05-14.

A grep for the same claim found a second copy in an engine string. The
remedy text of `goc validate`'s `PLUGIN_AND_VENDORED_HOOKS_DOUBLE_FIRE`
warning (`validate_plugin_hook_double_fire` in `goc/engine.py`) said
"switch to skills_source: plugin and remove .claude/hooks/". Deleting
`.claude/hooks/` by hand leaves the `.claude/settings.json` registrations
pointing at scripts that no longer exist. The pin edit on its own removes
nothing.

## Evidence

`reproduce.py` reads the recipe out of `goc.md` instead of restating it.
It applies the recipe to a scratch `goc install --local-skills` repo that
holds one skill the repo wrote itself, then runs one more routine
`goc upgrade`. Against the pre-fix text
(`git show 5be726c7:goc.md > /tmp/goc.md && reproduce.py /tmp/goc.md`),
it exits 1:

```
goc.md recipe: hand-delete .claude/skills/, .claude/hooks/ and the GoC settings entries
  install --local-skills + one user skill      {'user skill intact': True, 'GoC skill dirs': 16, 'GoC hook scripts': 3, 'GoC settings hook entries': 3, 'skills_source': 'vendored'}
  hand-delete                                  {'user skill intact': False, 'GoC skill dirs': 0, 'GoC hook scripts': 0, 'GoC settings hook entries': 0, 'skills_source': 'vendored'}
  the recipe's goc upgrade (exit 0)            {'user skill intact': False, 'GoC skill dirs': 16, 'GoC hook scripts': 3, 'GoC settings hook entries': 3, 'skills_source': 'vendored'}
  one more routine goc upgrade (exit 0)        {'user skill intact': False, 'GoC skill dirs': 16, 'GoC hook scripts': 3, 'GoC settings hook entries': 3, 'skills_source': 'vendored'}
```

Against the fixed text, it exits 0:

```
goc.md recipe: set skills_source: plugin, then goc upgrade (answer y)
  install --local-skills + one user skill      {'user skill intact': True, 'GoC skill dirs': 16, 'GoC hook scripts': 3, 'GoC settings hook entries': 3, 'skills_source': 'vendored'}
  the recipe's goc upgrade (exit 0)            {'user skill intact': True, 'GoC skill dirs': 0, 'GoC hook scripts': 0, 'GoC settings hook entries': 0, 'skills_source': 'plugin'}
  one more routine goc upgrade (exit 0)        {'user skill intact': True, 'GoC skill dirs': 0, 'GoC hook scripts': 0, 'GoC settings hook entries': 0, 'skills_source': 'plugin'}
```

The falsification recipe's second escape also failed to fire. `goc validate`
printed no warning on the half-migrated repo. That repo had no plugin
enabled, which is the only condition under which the double-fire warning
speaks.

Running the switch through the plugin's bundled engine
(`claude-plugin/bin/goc upgrade`, answering `y`) removed the hook scripts,
the bootstrap and the settings entries, but left all 16 GoC skill
directories in place. The bundled engine ships no `templates/skills/`.
The closed `strip-claude-vendored-harness-crashes-when-plugin-engine-omits-skill-templates`
made the cleanup skip skill-dir removal in that case instead of crashing.

## Fix

- **`goc.md` § "Coexistence with the repo-local harness"** now:
  - describes the vendored layout, including the `skills_source: vendored`
    pin, for `--local-skills` installs and for pre-plugin `--agents claude`
    installs;
  - gives the switch as two numbered steps: set `skills_source: plugin` in
    `.game-of-cards/config.yaml`, then run `goc upgrade` and answer `y`
    (`echo y | goc upgrade` when scripting it);
  - says the cleanup removes only GoC's skill dirs, hook scripts and
    settings entries, and keeps the repo's own;
  - says to run the switch with the standalone `goc`, not the plugin's
    bundled engine, which leaves GoC's skill dirs behind;
  - warns that a hand-delete loses the repo's skills and is undone by the
    next `goc upgrade`.
- **`goc/engine.py` `validate_plugin_hook_double_fire`**: the remedy now
  says to set `skills_source: plugin` and run `goc upgrade`, accepting its
  cleanup. `tests/test_validate_plugin_hook_double_fire.py` requires
  `goc upgrade` in the remedy and refuses `remove .claude/hooks`.
- **Guard: `tests/test_plugin_switch_recipe.py`** uses the run-it-against-a-fixture
  technique from the family card. It reads the numbered steps out of the
  section and runs them against a scratch `--local-skills` install that
  also holds a skill, a hook script and settings of the repo's own. It
  checks the repo ends in plugin mode with all three intact, and that the
  result survives a routine `goc upgrade`. The section's two warnings are
  executed and compared in both directions, so a behavior change on
  either side fails the build:
  - hand-deleting gets re-vendored;
  - the bundled engine leaves the skill dirs behind (asserted through the
    standalone-`goc` caveat).

  The guard also checks the vendored layout the section describes and
  refuses a `remove .claude/skills/` instruction. All five tests fail
  against the pre-fix text.

## Surfaced while fixing

- [upgrade-re-offers-the-plugin-cleanup-on-every-run-when-the-repo-keeps-its-own-skills](../upgrade-re-offers-the-plugin-cleanup-on-every-run-when-the-repo-keeps-its-own-skills/).
  After the documented switch, every later `goc upgrade` offered the
  cleanup again, claiming a "leftover .claude/skills/" because the
  directory still held the repo's own skill. Fixed through in the same
  session.
- [plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove](../plugin-engine-cleanup-leaves-every-goc-skill-dir-its-prompt-promises-to-remove/).
  The bundled engine's prompt promises to remove GoC's skill directories,
  then keeps all of them. Filed and left open. `goc.md`'s standalone-`goc`
  caveat stays until that card lands, and the guard above fails when it
  does.

Out of scope here: `goc.md` § "What the plugin provides" (`16 GoC skills
(same as goc install --agents claude)`) and `ABOUT.md`'s install-flag list
belong to
[install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag](../install-docs-still-describe-the-pre-plugin-install-model-and-a-removed-no-harness-flag/).

This is one more instance of the family tracked by
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/),
and has a row there.

Surfaced by: general-purpose audit hunter (human-facing docs vs code),
2026-09-28.
