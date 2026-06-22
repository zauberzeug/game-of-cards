---
title: openclaw-plugin-manifest-never-registers-the-upgrade-skill
summary: "The OpenClaw plugin payload shipped the `upgrade` skill as files but never registered it in `openclaw.plugin.json`'s hardcoded `skills` array, so OpenClaw never activated it. The porter's `--check`/`drifted_skills()` compared SKILL.md content only and did not verify manifest registration. Fixed by registering the skill and adding a parity guard (`OpenClawManifestSkillRegistrationTest`) linking the manifest array to the ported skill dirs."
status: done
stage: null
contribution: medium
created: "2026-06-21T11:37:47Z"
closed_at: "2026-06-21T11:41:16Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: a regression guard in tests/test_plugin_mirror_parity.py fails BEFORE the manifest fix (asserts every ported openclaw-plugin/skills/<dir> is listed in openclaw.plugin.json's skills array, and vice versa) and passes AFTER
  - [x] MECHANICAL: openclaw-plugin/openclaw.plugin.json skills array lists skills/upgrade
  - [x] MECHANICAL: the manifest description "15 deck skills" is corrected to "16 deck skills"
  - [x] EMPIRICAL: ported-dir set == manifest skills set (set difference is empty both ways), shown via reproduce.py output recorded in log.md
worker: {who: "claude[bot]", where: main}
---

# openclaw-plugin-manifest-never-registers-the-upgrade-skill

The OpenClaw plugin payload ships the `upgrade` skill as files but never
registers it in `openclaw.plugin.json`, so OpenClaw never activates it.
The manifest's hardcoded `skills` array predates the skill's existence,
and no drift guard links the array to the ported skill directories.

## Location

- `openclaw-plugin/openclaw.plugin.json` — the `skills` array (15 entries)
  and the `description` string ("…15 deck skills…").
- `openclaw-plugin/skills/upgrade/SKILL.md` — the ported-but-unregistered
  skill files.
- `scripts/port_skills_to_openclaw.py` — `--check` / `drifted_skills()`
  compares ported SKILL.md *content* only; it does not verify manifest
  registration.
- `tests/test_plugin_mirror_parity.py` — the CI parity test calls
  `drifted_skills()`, so it shares the same blind spot.

## What's broken

OpenClaw plugins register skills via an explicit `skills` array in the
manifest. `openclaw-plugin/openclaw.plugin.json` lists 15 entries:

```json
"skills": [
  "skills/deck", "skills/kickoff", "skills/openclaw-kickoff",
  "skills/scan-deck", "skills/next-card", "skills/create-card",
  "skills/advance-card", "skills/finish-card", "skills/decide-card",
  "skills/pull-card", "skills/refine-deck", "skills/audit-deck",
  "skills/standup", "skills/retrospective", "skills/card-schema"
]
```

and the description asserts:

```json
"description": "… a `goc` tool, three lifecycle hooks, and 15 deck skills …"
```

But the porter ships **16** skill directories — the array omits
`skills/upgrade`. The `upgrade` skill was added under
`goc/templates/skills/upgrade/` on 2026-05-30 (`f76dace`); the manifest's
`skills` array was last edited on 2026-05-10 (`417fbd9`), before the skill
existed. The porter (`scripts/port_skills_to_openclaw.py`) ports every
non-host-prefixed source skill, so it wrote
`openclaw-plugin/skills/upgrade/SKILL.md` — but nothing updated the
hand-maintained manifest array. Per AGENTS.md, `openclaw.plugin.json` is
explicitly NOT auto-synced, so this registration is human-maintained and
silently fell out of date.

The two existing drift guards do not catch it: `port_skills_to_openclaw.py
--check` and `tests/test_plugin_mirror_parity.py` only compare the
*content* of each ported `SKILL.md` against a fresh re-port. Neither
asserts that each ported skill dir appears in the manifest's `skills`
array. So the drift is CI-invisible.

## Empirical evidence

See [reproduce.py](reproduce.py). It compares the ported skill-dir set to
the manifest `skills` array and asserts the description count:

```
ported skill dirs (16): advance-card, audit-deck, card-schema, create-card,
  decide-card, deck, finish-card, kickoff, next-card, openclaw-kickoff,
  pull-card, refine-deck, retrospective, scan-deck, standup, upgrade
manifest skills (15): advance-card, audit-deck, card-schema, create-card,
  decide-card, deck, finish-card, kickoff, next-card, openclaw-kickoff,
  pull-card, refine-deck, retrospective, scan-deck, standup
ported but NOT registered in manifest: {'upgrade'}
manifest description claims: 15 deck skills (actual ported: 16)
DEFECT CONFIRMED
```

## Why it matters

Reachability: `scripts/port_skills_to_openclaw.py` walks every source
skill dir and writes a corresponding `openclaw-plugin/skills/<name>/`
tree — this is the shipping port path that produced
`openclaw-plugin/skills/upgrade/`. OpenClaw's plugin runtime registers
skills from the manifest's `skills` array (see
`openclaw-plugin/openclaw.plugin.json`), so a ported skill missing from
that array ships as dead files the host never activates. OpenClaw users
therefore cannot invoke the `upgrade` skill at all, and the plugin's own
self-description ("15 deck skills") is wrong. Because no guard links the
array to the ported set, the same silent gap recurs for every future
skill addition.

This is distinct from the closed cards
[openclaw-plugin-ported-skills-drift-silently-from-templates](../openclaw-plugin-ported-skills-drift-silently-from-templates/)
(SKILL.md content drift) and
[openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories](../openclaw-skill-porter-drops-sibling-asset-files-from-skill-directories/)
(sibling asset files) — both about the *contents* of ported dirs, not
about manifest registration of the dirs themselves.

## Fix

1. Add `"skills/upgrade"` to the `skills` array in
   `openclaw-plugin/openclaw.plugin.json` (keep the existing ordering
   convention — append after `card-schema` or wherever the source order
   places it).
2. Correct the `description` count from "15 deck skills" to "16 deck
   skills".
3. Add a regression guard so the array can never silently fall behind the
   ported set again: extend `tests/test_plugin_mirror_parity.py` with a
   test that loads `openclaw-plugin/openclaw.plugin.json`, collects the
   `skills` array, and asserts it equals the set of subdirectories under
   `openclaw-plugin/skills/` (symmetric difference empty). This lives in a
   test (not a `ci.yml` step) for the same reason the porter drift guard
   does — the autonomous bot's `GITHUB_TOKEN` cannot edit workflow files.
