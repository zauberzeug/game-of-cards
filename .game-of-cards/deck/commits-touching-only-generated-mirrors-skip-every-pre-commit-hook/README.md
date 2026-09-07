---
title: commits-touching-only-generated-mirrors-skip-every-pre-commit-hook
summary: "All four hooks in .pre-commit-config.yaml are pass_filenames: false whole-tree checks, but each is gated on a files: regex naming only part of the tree it checks — so a commit that edits only a generated mirror (codex-plugin/, openclaw-plugin/, .claude/skills/, .codex/skills/, .claude/hooks/) matches no filter and pre-commit reports \"(no files to check) Skipped\" for every hook, exit 0. The same working tree fails CI: goc validate exits 1 on plugin mirror drift and sync_plugin_assets.py --check exits 1 on both files. AGENTS.md states the sync hook regenerates mirrors \"on every commit\" and that a hand-edited mirror \"gets overwritten by the next pre-commit pass\" — the files: filters make both claims false."
status: done
stage: null
contribution: medium
created: "2026-08-24T05:25:29Z"
closed_at: "2026-08-24T05:33:08Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — every mirror path `goc validate` /
    `sync_plugin_assets.py --check` guard triggers at least one pre-commit hook.
  - [x] TDD: a regression test in `tests/` asserts each `pass_filenames: false`
    hook in `.pre-commit-config.yaml` is reachable from a commit confined to any
    tree its check reads, and fails on today's `files:`-only config.
  - [x] MECHANICAL: `.pre-commit-config.yaml` is fixed so the local hook set is
    the mirror of the CI check set, with the reason recorded in the file.
  - [x] MECHANICAL: cross-referenced from
    [pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/)
    as the second, independent reason pre-commit does not fire.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` green and
    `uv run goc validate` clean.
worker: {who: "claude[bot]", where: main}
---

# Commits touching only generated mirrors skip every pre-commit hook

## Location

`.pre-commit-config.yaml` — all four hooks:

```yaml
- id: sync-plugin-assets
  entry: uv run python scripts/sync_plugin_assets.py
  pass_filenames: false
  files: ^goc/
- id: goc-validate
  entry: uv run goc validate
  pass_filenames: false
  files: ^(\.game-of-cards/deck/|goc/|claude-plugin/).*$
- id: card-language
  entry: uv run python scripts/check_card_language.py --check
  pass_filenames: false
  files: ^\.game-of-cards/deck/.*$
- id: card-frontmatter-yaml
  entry: uv run python scripts/check_card_frontmatter_yaml.py --check
  pass_filenames: false
  files: ^\.game-of-cards/deck/.*$
```

## What's broken

Every one of these hooks is `pass_filenames: false` — it re-checks the whole
tree and ignores which files changed. The `files:` key is therefore not a
*scope*; it is only a *trigger*. And pre-commit skips a hook whose filtered
file list comes out empty: `always_run` defaults to `false`, so a hook whose
`files:` pattern matches none of the staged paths is reported as
`(no files to check) Skipped`.

The checks read considerably more of the tree than the triggers name.
`goc validate` runs `validate_plugin_mirror_parity` (`goc/engine.py:1552`) over
`claude-plugin/`, `codex-plugin/` and `openclaw-plugin/`;
`scripts/sync_plugin_assets.py --check` compares those three payloads plus this
repo's dogfood self-host copies under `.claude/skills/`, `.claude/hooks/` and
`.codex/skills/` (`scripts/sync_plugin_assets.py:7-11`). Of those six trees only
`claude-plugin/` appears in a `files:` pattern.

So a commit confined to a generated mirror satisfies no trigger, fires no hook,
and lands clean. The very next CI run fails on it. AGENTS.md § "Skill and hook
files have two copies" states the opposite contract:

> the `sync-plugin-assets` pre-commit hook regenerates those mirrors from the
> templates **on every commit** and stages them automatically

and, of a hand-edited mirror:

> editing only `.claude/skills/...` or `.codex/skills/...` is now CI-detectable
> (**it gets overwritten by the next pre-commit pass**)

Neither holds. The sync hook does not run on every commit — it runs on commits
touching `goc/`. A mirror hand-edit is not overwritten by the next pre-commit
pass, because that pass does not run.

This is the same drift that
[goc-upgrade-leaves-stale-pre-commit-validate-pattern](../goc-upgrade-leaves-stale-pre-commit-validate-pattern/)
already hit once: a `files:` glob silently stopped matching the tree its hook
guards, and the gate went dead without a symptom. There the glob had gone stale
against a moved deck; here it never covered the mirrors that were added after it
was written.

## Empirical evidence

Drift both a plugin mirror and a dogfood skill mirror, then run pre-commit
against exactly those two paths:

```
$ printf '\n# DRIFT MARKER\n' >> codex-plugin/goc/engine.py
$ printf '\nDRIFT MARKER\n'   >> .claude/skills/deck/SKILL.md
$ pre-commit run --files codex-plugin/goc/engine.py .claude/skills/deck/SKILL.md
sync plugin assets from goc/ to claude-plugin/.......(no files to check)Skipped
goc validate.........................................(no files to check)Skipped
cards are written in English.........................(no files to check)Skipped
card frontmatter is valid YAML.......................(no files to check)Skipped
exit=0
```

The identical working tree fails both CI checks:

```
$ uv run goc validate ; echo exit=$?
ERROR: plugin mirror drift: goc vs codex-plugin/goc: engine.py (differs)
exit=1

$ uv run python scripts/sync_plugin_assets.py --check ; echo exit=$?
ERROR: sync targets are out of sync with goc/ + goc/templates/:
  codex-plugin/goc/engine.py
  .claude/skills/deck/SKILL.md
Fix: run `python scripts/sync_plugin_assets.py` and commit the result.
exit=1
```

`reproduce.py` derives the same verdict statically from the config, so it needs
no pre-commit installation and modifies nothing:

```
  sync-plugin-assets       always_run=False files=^goc/
  goc-validate             always_run=False files=^(\.game-of-cards/deck/|goc/|claude-plugin/).*$
  card-language            always_run=False files=^\.game-of-cards/deck/.*$
  card-frontmatter-yaml    always_run=False files=^\.game-of-cards/deck/.*$

  codex-plugin/goc/engine.py               -> NOTHING FIRES
  codex-plugin/skills/deck/SKILL.md        -> NOTHING FIRES
  openclaw-plugin/goc/engine.py            -> NOTHING FIRES
  .claude/skills/deck/SKILL.md             -> NOTHING FIRES
  .codex/skills/deck/SKILL.md              -> NOTHING FIRES
  .claude/hooks/deck_session_start.py      -> NOTHING FIRES

FAIL: 6 guarded path(s) trigger no pre-commit hook
```

## Why it matters

The mirror trees are exactly where a hand-edit is *expected* — AGENTS.md has to
warn against editing them precisely because they look like ordinary source. The
hook that is supposed to catch and repair that mistake is the one guaranteed not
to fire when the mistake is made in isolation.

The cost is a red build on `main` plus a round trip, not silent corruption: CI
does catch it. But this repo's bot pushes straight to `main`, so a red build
there blocks the next agent rather than a pull request.

This is a **different** root cause from
[pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate](../pull-card-workflow-skips-pre-commit-so-bot-commits-bypass-goc-validate/),
which reports that `.github/workflows/pull-card.yml` never installs pre-commit
at all. That card is about the bot never running the hooks; this one is about
the hooks declining to run for a human who has them installed. They are also
disjoint in fix location — that one needs a human commit under
`.github/workflows/` (the bot's `GITHUB_TOKEN` cannot write there), this one is
a repo-root config the bot can land.

## Fix (landed)

All four hooks now carry `always_run: true` and no `files:` filter. A
`pass_filenames: false` hook already declares "I check the whole tree";
`always_run: true` is pre-commit's documented way to say "so run me whenever
anything is committed", and it is the only form that cannot drift again as
`goc validate` or the sync script learn new surfaces. Measured cost of the full
set on this repo is ~1.5s (`sync_plugin_assets` 0.17s, `goc validate` 0.58s,
`check_card_language` 0.54s, `check_card_frontmatter_yaml` 0.18s), which makes
the local hook set the exact mirror of what CI runs unconditionally.

The alternative considered and rejected: widen each `files:` regex to enumerate
every tree its check reads. It restores today's behaviour for today's surfaces,
but it re-creates the failure mode — a seventh mirror, or a new validator
surface, silently falls out of the pattern with no symptom. That is precisely
how `goc-upgrade-leaves-stale-pre-commit-validate-pattern` happened, and it buys
about a second per commit.

`always_run: true` and `files:` are not mutually exclusive in pre-commit's
schema — a config carrying both is accepted, and `always_run` wins — but the
filter is then dead weight that reads as a live scope, so it was removed rather
than left in place.

## Verification

The same drift that used to sail through now stops the commit, and the sync hook
repairs it in the same pass — the contract AGENTS.md always claimed:

```
$ printf '\n# DRIFT MARKER\n' >> codex-plugin/goc/engine.py
$ printf '\nDRIFT MARKER\n'   >> .claude/skills/deck/SKILL.md
$ pre-commit run --files codex-plugin/goc/engine.py .claude/skills/deck/SKILL.md
sync plugin assets from goc/ to claude-plugin/...........................Failed
- hook id: sync-plugin-assets
- files were modified by this hook

sync-plugin-assets: synced 2 file(s), staged for commit.

goc validate.............................................................Passed
cards are written in English.............................................Passed
card frontmatter is valid YAML...........................................Passed
exit=1
```

(`goc validate` passes on the second line because the sync hook, running first,
already repaired the drift it would otherwise have reported.)

`reproduce.py` now exits zero, reporting every guarded path as covered by all
four hooks. `tests/test_precommit_hook_reachability.py` pins the invariant in
the regression suite: it fails on any `pass_filenames: false` hook that a commit
could filter out, and failed 50 subtests against the pre-fix config.

Regression suite: 1033 tests, OK. `uv run goc validate` exit 0.
`python scripts/sync_plugin_assets.py --check` clean.
