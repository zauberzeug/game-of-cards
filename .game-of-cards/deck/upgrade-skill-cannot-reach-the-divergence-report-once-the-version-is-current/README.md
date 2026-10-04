---
title: upgrade-skill-cannot-reach-the-divergence-report-once-the-version-is-current
summary: "FIXED: goc upgrade printed the divergence report that Skill(upgrade) reads only on a run with effecting writes. At the current version it returned 'already at goc X — nothing to do.' first, and a diverged evolving file is a no-op (preserved) to the plan gating that return, so the skill's own run got no report whenever someone had already upgraded, as the install output tells them to. The no-op path now prints the same read-only report, and the skill names plain goc upgrade as its whole invocation."
status: done
stage: null
contribution: medium
created: "2026-09-28T01:33:12Z"
closed_at: "2026-10-04T07:18:26Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] TDD: a reproduce.py upgrades a scratch install to the current version, diverges `.game-of-cards/README.md` from its template, then runs `goc upgrade` again and asserts the divergence report is printed — or the run disproves the hypothesis and the card flips to `disproved`
  - [x] TDD: a regression test pins that the report is reachable at the current version (a `goc upgrade` that is otherwise a no-op still prints it, or a flag the skill uses does)
  - [x] MECHANICAL: `upgrade/SKILL.md` names the invocation that yields the report on a no-op upgrade, and its "next time someone runs this skill" promise (line 130) holds; drop the `unverified` tag once reproduce.py lands
worker: {who: "claude[bot]", where: main}
---

# The upgrade skill cannot reach the divergence report once the version is current

> **FIXED 2026-10-04.** Verified by `reproduce.py` (exit 1 before the fix,
> exit 0 after). `goc upgrade` now prints the divergence report on its
> "nothing to do" path too, and `Skill(upgrade)` says plain `goc upgrade`
> yields it on every run.

## Location

- `goc/templates/skills/upgrade/SKILL.md:45-52`, step 1: "Run
  `goc upgrade` and capture stdout." Every later step of the skill reads
  the sentinel-marked JSON report that run prints.
- `goc/install.py:2122-2140`, `upgrade()`'s short-circuit: once
  `existing == __version__` and no planned write has an effect, it prints
  `already at goc {__version__} — nothing to do.` and returns.
- `goc/install.py:2176`,
  `_sync_game_of_cards_config(target, templates, migrate_legacy=True, emit_report=True)`:
  before the fix, the only call that printed the report, below that
  return.
- `goc/install.py:108`,
  `_NO_OP_ACTIONS = frozenset({"unchanged", "preserved"})`. A diverged
  evolving file is `preserved`, a no-op, so the very divergence the skill
  exists to reconcile never made the plan effecting.

## Defect (verified)

The skill's catch-up path could not be reached. It promises that upstream
changes to the two *evolving* files (`README.md`, `config.yaml`) "sit in
the template payload until the next time someone runs this skill", and it
rules out re-running the engine. But its step 1 *is* a `goc upgrade` run,
and at the current version that run printed the no-op line and no report.
That is the ordinary state by the time the skill runs:

- a human ran `goc upgrade` in a terminal first, as the install output
  tells them to (`goc/install.py:1955`, "Run `goc upgrade` later to sync
  template updates");
- an earlier skill session ended after the engine step.

The upstream changes then went un-reconciled until the next version bump.
Only an explicit agent flag (`goc upgrade --claude`, which sets
`agents_explicit` and so skips the short-circuit) printed the report, and
the skill never mentioned it.

## Verification

`reproduce.py` installs a scratch repo, rewinds the sentinel to `0.0.1`,
upgrades to the current version, appends a line to
`.game-of-cards/README.md`, then runs `goc upgrade` again through
`python -m goc.cli`, as a consumer would. Before the fix:

```
[1] goc upgrade 0.0.1 -> 0.0.27.post1.dev487: exit 0
    printed report: True
[3] goc upgrade at 0.0.27.post1.dev487: exit 0
    first line: already at goc 0.0.27.post1.dev487 — nothing to do.
    printed report: False
DEFECT PRESENT (1 failure(s))
```

After the fix, the second run prints the report with
`{"path": "README.md", "status": "preserved", "ownership": "evolving"}`,
writes nothing, and the script exits 0.

## Fix

The card's recommended direction: the short-circuit prints the
divergence report after its verdict line
(`_emit_divergence_report(_user_owned_classifications(...))`). It is
read-only, so the no-op still writes nothing, and the skill's step 1
works whether or not someone ran the engine first. The alternative, a
flag the skill would have to pass (`--claude`, or a new `--report-only`),
was rejected because it adds CLI surface and leaves bare `goc upgrade`
unable to feed the skill.

The short-circuit sits before the `--dry-run` branch, so the no-op
preview prints the report too and stays byte-identical to the real
no-op. An *effecting* `--dry-run` still prints only its plan, whose
`.game-of-cards/` rows carry the same create / unchanged / preserved
labels. The skill never runs a dry-run.

Regression tests: `tests/test_upgrade_reports_divergence_at_current_version.py`
covers the no-op report, its equality with the report the preceding
effecting run printed, and the no-op preview. The pristine no-op test in
`tests/test_upgrade_repairs_damaged_install_at_same_version.py` now pins
the exact verdict line followed by the report and nothing else. Before,
it pinned the verdict line as the whole output.

Related:
[upgrade-divergence-report-marks-pristine-config-as-authored-divergence](../upgrade-divergence-report-marks-pristine-config-as-authored-divergence/)
(decision-gated) is about what the report says, not whether it is
printed.

Surfaced by: general-purpose audit hunter (shipped skills vs CLI
contract), 2026-09-28.
