---
title: upgrade-skill-cannot-reach-the-divergence-report-once-the-version-is-current
summary: "UNVERIFIED. Skill(upgrade) reads only the engine's sentinel-marked divergence report, but goc upgrade prints it only on a run with effecting writes: at the current version it returns early with 'already at goc X — nothing to do.' and no report, and a diverged evolving file counts as a no-op. So the skill's promised catch-up (the upstream changes wait until the next time someone runs this skill) is unreachable whenever someone ran goc upgrade first, as the install output tells them to."
status: open
stage: null
contribution: medium
created: "2026-09-28T01:33:12Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation, unverified]
definition_of_done: |
  - [ ] TDD: a reproduce.py upgrades a scratch install to the current version, diverges `.game-of-cards/README.md` from its template, then runs `goc upgrade` again and asserts the divergence report is printed — or the run disproves the hypothesis and the card flips to `disproved`
  - [ ] TDD: a regression test pins that the report is reachable at the current version (a `goc upgrade` that is otherwise a no-op still prints it, or a flag the skill uses does)
  - [ ] MECHANICAL: `upgrade/SKILL.md` names the invocation that yields the report on a no-op upgrade, and its "next time someone runs this skill" promise (line 130) holds; drop the `unverified` tag once reproduce.py lands
---

# The upgrade skill cannot reach the divergence report once the version is current

> **UNVERIFIED.** Surfaced by an audit hunter on the shipped-skills-vs-CLI
> seam on 2026-09-28. The filing agent re-read and confirmed the
> citations. No `reproduce.py` was written this round; the falsification
> recipe is below.

## Location

- `goc/templates/skills/upgrade/SKILL.md:45-47`, step 1: "Run
  `goc upgrade` and capture stdout. The engine emits a sentinel-marked
  JSON divergence report after its normal upgrade output". Every later
  step reads that report.
- `goc/install.py:2085-2096` returns early: once
  `existing == __version__` and no planned write has an effect, it prints
  `already at goc {__version__} — nothing to do.` and returns.
- `goc/install.py:2132`:
  `_sync_game_of_cards_config(target, templates, migrate_legacy=True, emit_report=True)`.
  This is the only call that prints the report, and it sits after the
  early return.
- `goc/install.py:108`:
  `_NO_OP_ACTIONS = frozenset({"unchanged", "preserved"})`. A diverged
  evolving file is `preserved`, a no-op, so the very divergence the skill
  exists to reconcile never makes the plan effecting.

## Hypothesis

The skill's catch-up path cannot be reached. It promises
(`upgrade/SKILL.md:129-130`):

> the upstream changes sit in the template payload until the next time
> someone runs this skill

It also rules out re-running the engine (`:136-138`):

> Does NOT re-run `goc upgrade`. … Re-running would be a no-op (version
> is now current).

But the skill's step 1 *is* a `goc upgrade` run. Whenever the version is
already current, that run prints `nothing to do.` and no report. This
happens in two ordinary cases:

- a human ran `goc upgrade` in a terminal first, as the install output at
  `goc/install.py:1920` tells them to ("Run `goc upgrade` later to sync
  template updates");
- an earlier skill session ended after the engine step.

`goc upgrade --dry-run` does not print the report either. The hunter
found that an explicit agent flag (`goc upgrade --claude`) bypasses the
short-circuit (`agents_explicit`) and does print the report, but the
skill never mentions it. The upstream changes to the two *evolving*
files, `README.md` and `config.yaml`, then go un-reconciled until the
next version bump.

## Why deferred

The citations are confirmed. The hunter's scratch run printed:

- `terminal upgrade printed report: True`
- `skill's goc upgrade output: already at goc 0.0.27 — nothing to do.`
- `skill's goc upgrade printed report: False`
- `--dry-run printed report: False`

No `reproduce.py` is committed this round.

## Fix direction

Recommended: print the divergence report on the `nothing to do` path
too. It is read-only, and it is the skill's only input. The skill's
contract then holds whether or not someone ran the engine first.

Alternative: document `goc upgrade --claude` (or a dedicated
`--report-only`) as the skill's step-1 invocation. That keeps the
short-circuit silent, at the cost of a flag the skill must remember.

Related:
[upgrade-divergence-report-marks-pristine-config-as-authored-divergence](../upgrade-divergence-report-marks-pristine-config-as-authored-divergence/)
(open) is about what the report says, not whether it is printed.

## Falsification recipe

1. In a scratch repo, run `goc install`.
2. Append a line to `.game-of-cards/README.md`.
3. Run `goc upgrade` twice.
4. Assert that the second run's stdout contains
   `GoC project-state divergence report (JSON):`. If it does, the
   hypothesis is disproved.

Surfaced by: general-purpose audit hunter (shipped skills vs CLI
contract), 2026-09-28.
