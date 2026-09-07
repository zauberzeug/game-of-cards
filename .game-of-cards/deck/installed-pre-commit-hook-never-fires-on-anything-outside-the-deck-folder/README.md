---
title: installed-pre-commit-hook-never-fires-on-anything-outside-the-deck-folder
summary: "goc install writes a goc-validate pre-commit hook that is pass_filenames: false — it re-checks the whole repo — yet gates it on files: ^\\.game-of-cards/deck/.*$ (goc/install.py:64-73). pre-commit skips a hook whose filtered file list is empty, so in a skills_source: vendored consumer a commit that only drifts .claude/skills/ or .codex/skills/ fires nothing, even though goc validate would report it through validate_skill_dir_parity. Same shape as commits-touching-only-generated-mirrors-skip-every-pre-commit-hook, which fixed this repo own config on 2026-08-24; this card is the consumer-facing half."
status: done
stage: null
contribution: medium
created: "2026-08-24T05:34:00Z"
closed_at: "2026-08-25T04:53:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — every surface that changes what
    `goc validate` reports in a consuming repo can trigger the shipped hook.
  - [x] MECHANICAL: `PRE_COMMIT_HOOK` in `goc/install.py` no longer gates a
    `pass_filenames: false` check behind a partial `files:` filter.
  - [x] TDD: a regression test pins the shipped block's shape and fails on the
    current `files:`-only form.
  - [x] MECHANICAL: existing installs are migrated. The rewrite path introduced
    by `goc-upgrade-leaves-stale-pre-commit-validate-pattern` needed no
    extension: `_refresh_goc_validate_block` replaces the whole GoC-signature
    stanza with the current `PRE_COMMIT_HOOK` rather than substituting one
    glob, so the `files:` → `always_run:` migration came for free, at install,
    at upgrade, and at the same-version short-circuit. Regression tests were
    added for the deck-scoped legacy block; the byte-identical no-op on an
    already-current block is unchanged.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` green and
    `uv run goc validate` clean; plugin mirrors resynced
    (`python scripts/sync_plugin_assets.py --check`).
worker: {who: "claude[bot]", where: main}
---

# The installed pre-commit hook never fires on anything outside the deck folder

## Location

`goc/install.py` — the block `goc install` / `goc upgrade` merge into a
consuming repo's `.pre-commit-config.yaml`. As it ships now:

```python
PRE_COMMIT_HOOK = """\
  - repo: local
    hooks:
      - id: goc-validate
        name: goc validate
        entry: goc validate
        language: system
        pass_filenames: false
        always_run: true
"""
```

The last line was `files: ^\\.game-of-cards/deck/.*$` until this card closed.

## What was broken

`pass_filenames: false` says this hook re-checks the whole repository and
ignores which files changed — and `goc validate` does exactly that. The
`files:` key is therefore not a scope but a *trigger*, and pre-commit skips a
hook whose filtered file list comes out empty (`always_run` defaults to false;
the run prints `(no files to check) Skipped`).

So the gate covered the deck folder and nothing else. In a `skills_source:
vendored` consumer that left a real hole: `_cmd_validate` (`goc/engine.py:4340`)
runs `validate_skill_dir_parity`, which walks `.claude/skills/` and
`.codex/skills/` and errors when the consumer's vendored copies are missing
skills the installed templates ship. Neither path could trigger the hook that
would report it. The two files that decide *whether that check runs at all* —
`.game-of-cards/config.yaml`'s `skills_source` key, and `.claude/settings.json`
when the key is `auto` or unset (`goc/engine.py:5449-5457`) — were equally
invisible to the filter.

This is the consumer-facing half of
[commits-touching-only-generated-mirrors-skip-every-pre-commit-hook](../commits-touching-only-generated-mirrors-skip-every-pre-commit-hook/),
which found and fixed the same shape in this repo's own hand-maintained
`.pre-commit-config.yaml` on 2026-08-24. That card's fix does not reach here:
this repo's config is a hand-edited local file, while `PRE_COMMIT_HOOK` is the
literal shipped into every repo `goc install` touches.

It is also the second time a `files:` glob on this exact hook has stopped
matching the tree it guards. In
[goc-upgrade-leaves-stale-pre-commit-validate-pattern](../goc-upgrade-leaves-stale-pre-commit-validate-pattern/)
the glob was `^deck/.*$` after the deck moved, so the gate matched no real card
path and was silently dead. That was fixed by correcting the pattern — which
left the mechanism that produced the failure in place.

## Empirical evidence

`reproduce.py` reads the shipped literal and applies pre-commit's own trigger
rule to each surface. Before the fix, 4 of the 5 surfaces `goc validate` reads
could not trigger the hook that reports them:

```
  pass_filenames=False  always_run=False  files='^\\.game-of-cards/deck/.*$'

  .game-of-cards/deck/some-card/README.md      fires    (validate_card / validate_deck_directories)
  .claude/skills/deck/SKILL.md                 SKIPPED  (validate_skill_dir_parity, in skills_source: vendored)
  .codex/skills/deck/SKILL.md                  SKIPPED  (validate_skill_dir_parity, in skills_source: vendored)
  .game-of-cards/config.yaml                   SKIPPED  (sets skills_source -> whether the parity check runs at all)
  .claude/settings.json                        SKIPPED  (effective_skills_source reads it when skills_source is auto/unset)

FAIL: the hook is pass_filenames: false (it checks the whole repo) but 4 surface(s)
its own check reads cannot trigger it
```

After the fix, every surface fires and the script exits 0:

```
  pass_filenames=False  always_run=True  files=None

  .game-of-cards/deck/some-card/README.md      fires    (validate_card / validate_deck_directories)
  .claude/skills/deck/SKILL.md                 fires    (validate_skill_dir_parity, in skills_source: vendored)
  .codex/skills/deck/SKILL.md                  fires    (validate_skill_dir_parity, in skills_source: vendored)
  .game-of-cards/config.yaml                   fires    (sets skills_source -> whether the parity check runs at all)
  .claude/settings.json                        fires    (effective_skills_source reads it when skills_source is auto/unset)

OK: every surface goc validate reads can trigger the shipped hook.
```

The behaviour of a filtered whole-tree hook was confirmed directly against
pre-commit 4.6.2 while closing the sibling card: with `always_run: true` the
hook runs on a non-matching path (`Passed`); with the key removed the same run
prints `(no files to check) Skipped`.

## Why it mattered

Every repo `goc install` has ever touched carries this block, and the hole was
exactly where a consumer is told the gate protects them. It was worse in a
consuming repo than it was here: this repo has CI running `goc validate`
unconditionally as a backstop, and a fresh consumer has whatever CI it wrote
itself — often none.

## Fix (applied)

What the sibling card landed for this repo's own config, applied to the shipped
literal: `files:` dropped, `always_run: true` added. The hook already declares
itself a whole-tree check, so this is the shape that matches its own semantics,
and it cannot drift again as `goc validate` learns new surfaces — the failure
mode both prior incidents share. Cost is one `goc validate` per commit (≈0.6s
on this repo's 736-card deck).

The migration turned out to be free rather than the larger half. The card
assumed the rewrite path introduced by
[goc-upgrade-leaves-stale-pre-commit-validate-pattern](../goc-upgrade-leaves-stale-pre-commit-validate-pattern/)
would have to be *extended* to recognise a `files:`-gated block. It does not:
`_refresh_goc_validate_block` matches the GoC-signature stanza and replaces the
whole thing with the current `PRE_COMMIT_HOOK`, so it carries any change to the
literal forward — not just the one glob substitution it was written for. That
generality is what made this fix a one-line template edit. Both of its
guarantees still hold and are still pinned by test: a non-GoC `repo: local`
hook elsewhere in the file is preserved untouched, and an already-current block
is left byte-identical. The same-version `upgrade()` short-circuit already
consults `_precommit_refresh_pending`, so a consumer sitting on the current
version still gets the migration.

Where the fix landed:

- `goc/install.py` — `PRE_COMMIT_HOOK`, plus a comment recording why a whole-tree
  hook must not carry a `files:` filter; docstrings of
  `_refresh_goc_validate_block` / `_precommit_refresh_pending` and the
  `upgrade()` comment generalised from "the legacy glob" to "any drifted
  stanza".
- `tests/test_precommit_hook_reachability.py` — new
  `ShippedPreCommitHookReachability`, reusing the `parse_hooks` / `triggers`
  helpers the sibling card wrote for this repo's own config. One statement of
  the invariant, now applied to both configs.
- `tests/test_install.py` — `RefreshStalePrecommitHookTest` gains the
  deck-scoped legacy block alongside the pre-move one, and asserts against
  `PRE_COMMIT_HOOK` itself rather than a literal glob.
- `tests/test_upgrade_precommit_refresh_at_same_version.py` — same
  assert-against-the-literal change, so neither file needs editing the next
  time the stanza evolves.

The three open cards that also rewrite this literal or its merge path —
[install-writes-pre-commit-entry-that-fails-on-plugin-only-hosts](../install-writes-pre-commit-entry-that-fails-on-plugin-only-hosts/),
[install-corrupts-pre-commit-config-in-the-style-pre-commit-itself-generates](../install-corrupts-pre-commit-config-in-the-style-pre-commit-itself-generates/),
and [install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key](../install-corrupts-pre-commit-config-when-repos-is-not-the-last-top-level-key/)
— are all parked at `human_gate: decision` and untouched by this change, which
alters only *when* the stanza fires. The first of them quoted the old literal in
its Location section; that quote was amended in place so the parked card does
not advertise code that no longer exists.
