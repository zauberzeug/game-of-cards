---
title: derive-openclaw-manifest-skills-array-from-ported-skill-dirs
summary: "The `skills` array (and '<N> deck skills' description count) in `openclaw-plugin/openclaw.plugin.json` is hand-maintained and silently drifted once — the `upgrade` skill shipped as dead files for ~3 weeks. A parity guard now detects drift but does not eliminate the hand-maintenance class. Decision card: derive the array + count from the ported skill dirs in `scripts/port_skills_to_openclaw.py` (mirroring the Claude hook-manifest derivation), or keep it hand-maintained with the guard as the chosen contract."
status: open
stage: null
contribution: medium
created: "2026-06-21T11:42:33Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] PROCESS: decision recorded below — derive the manifest skills array (and description count) from the ported set, OR keep it hand-maintained with the existing parity guard as the chosen contract
  - [ ] (replace remaining criteria once the approach is chosen)
---

# derive-openclaw-manifest-skills-array-from-ported-skill-dirs

The `skills` array in `openclaw-plugin/openclaw.plugin.json` is
hand-maintained and silently drifted from the ported skill set (see the
closed card
[openclaw-plugin-manifest-never-registers-the-upgrade-skill](../openclaw-plugin-manifest-never-registers-the-upgrade-skill/):
the `upgrade` skill shipped as dead files for ~3 weeks because nobody
added it to the array). That bug is now closed and a parity guard
(`OpenClawManifestSkillRegistrationTest`) makes the drift CI-visible —
but the guard only *detects* drift after a human forgets; it does not
eliminate the hand-maintenance class.

This card asks whether to close the class at the root by **deriving**
the manifest's `skills` array (and the "<N> deck skills" description
count) from the ported skill directories, the same way
[derive-claude-hook-manifest-from-templates](../derive-claude-hook-manifest-from-templates/)
already derives the Claude hook list from `templates/hooks/*.py` instead
of hand-maintaining it.

## Why it matters

`openclaw.plugin.json` is explicitly NOT auto-synced (per AGENTS.md), so
every skill addition requires a human to remember three coupled edits:
port the skill, add the array entry, bump the count. The same coupling
already bit once. The pattern — a hand-maintained enumeration that must
stay in lockstep with a derived/ported set — is exactly what the Claude
hook-manifest derivation removed on its side. The OpenClaw skills array
and description count are the remaining instance.

## Decision required

Pick the contract for keeping `openclaw.plugin.json`'s skill enumeration
correct:

- **Option A — Derive in the porter.** Have
  `scripts/port_skills_to_openclaw.py` rewrite the manifest's `skills`
  array and the "<N> deck skills" description count from the ported
  skill-dir set on every port (mirroring the Claude hook-manifest
  derivation). The hand-maintenance class disappears; the parity guard
  becomes a redundant backstop. Cost: the porter now mutates
  `openclaw.plugin.json`, a file currently in the "NOT auto-synced"
  set — AGENTS.md and the sync/porter contract docs must be updated to
  reflect that the `skills` array + count are now generated while the
  rest of the manifest stays hand-authored.

- **Option B — Keep hand-maintained, rely on the guard.** Accept the
  manifest as fully hand-authored and treat
  `OpenClawManifestSkillRegistrationTest` as the contract: drift turns
  CI red, a human fixes it. Cheaper now, but every future skill
  addition still needs the human to remember the array + count edits
  (the guard tells them *after* they forget, on a red build).

- **Option C — Partial derivation.** Generate only the `skills` array
  from ported dirs; leave the description prose (including the count)
  hand-authored, with the guard covering the count. Splits the
  difference but leaves the count coupling intact.

Open sub-questions for A/C: does the porter preserve the array's current
ordering convention, or emit a deterministic sorted order? Does
`--check` then also assert the manifest matches the derived output (like
the skill-content drift check already does)?

## Fix

Deferred until the option above is chosen. Whichever path wins, the
existing parity guard in `tests/test_plugin_mirror_parity.py` stays as
the safety net; Option A would additionally make it near-impossible to
trip.
