---
title: goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration
status: done
stage: null
contribution: medium
created: "2026-06-29T01:59:31Z"
closed_at: "2026-06-29T02:04:18Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [x] TDD: reproduce.py drives the real `upgrade()` flow on a repo whose
        `.goc-version` equals the current `__version__` and a
        `.pre-commit-config.yaml` carrying a legacy `files: ^deck/.*$`
        glob; it asserts the glob stays stale before the fix.
  - [x] MECHANICAL: `upgrade()`'s same-version "nothing to do"
        short-circuit no longer fires when the pre-commit goc-validate
        stanza would be refreshed by `_append_precommit_hook`.
  - [x] MECHANICAL: the existing "already at goc X — nothing to do"
        no-op path is preserved for a pristine, already-current repo
        (no spurious upgrade, message unchanged).
  - [x] EMPIRICAL: reproduce.py passes after the fix (legacy glob is
        migrated to the `.game-of-cards/deck` path).
  - [x] PROCESS: regression test added under tests/ and the full suite
        + `goc validate` stay green; plugin mirrors re-synced.
worker: {who: "claude[bot]", where: main}
---

# goc-upgrade-same-version-short-circuit-skips-the-pre-commit-glob-migration

## Summary

`goc upgrade`'s same-version short-circuit in `upgrade()`
(`goc/install.py:1720-1730`) returns *before* `_append_precommit_hook`
is ever called (`goc/install.py:1788`). So when a repo is already at the
current `goc` version, a stale legacy `files: ^deck/.*$` glob in
`.pre-commit-config.yaml` is never migrated — the very repair that the
closed card `goc-upgrade-leaves-stale-pre-commit-validate-pattern` added
is unreachable from the most common upgrade invocation.

## The defect

The "nothing to do" guard:

```python
# goc/install.py:1720
if (
    existing == __version__
    and not dry_run
    and not agents_explicit
    and not pending_cleanup
    and not keep_local_skills
    and not pending_briefing_migration
    and briefing_target is None
):
    print(f"already at goc {__version__} — nothing to do.")
    return
```

returns at line 1730. `_append_precommit_hook(target / ".pre-commit-config.yaml")`
is at line 1788 — past the `return`. The guard already carves out
*specific* pending work that must run even at the same version
(`pending_cleanup`, `pending_briefing_migration`), but a stale
pre-commit glob is not one of those signals, so the migration is
skipped.

`_append_precommit_hook` → `_refresh_goc_validate_block` is idempotent
(byte-identical no-op when the stanza already matches; only a single
GoC-signature `repo: local` block is touched), so running it on a
same-version repo is safe — it only ever *fixes* a drifted stanza.

## Reachability

A consumer who installed an older `goc`, has a `.pre-commit-config.yaml`
with the legacy `^deck/.*$` glob, then `pip install -U`'d to the current
version and re-ran `goc upgrade` at the same version (e.g. after a first
upgrade was interrupted before the precommit append, or the glob was
hand-reverted) keeps the dead glob. The goc-validate pre-commit hook
then matches no real card path under `.game-of-cards/deck/`, silently
disabling the frontmatter-drift gate — the exact failure mode the
predecessor card was filed to close.

## Relationship to the closed predecessor

`goc-upgrade-leaves-stale-pre-commit-validate-pattern` (done) fixed the
short-circuit *inside* `_append_precommit_hook` (`if "id: goc-validate"
in text: return`) and added `_refresh_goc_validate_block`. Its
`reproduce.py` exercises `_append_precommit_hook` **directly**, so it
never traverses `upgrade()`'s own short-circuit and could not catch this
caller-side gap. This card fixes the *caller*.

## Proposed fix

Mirror the existing `pending_*` pattern: compute a
`pending_precommit_refresh` boolean (true iff a `.git` dir + a
`.pre-commit-config.yaml` with a goc-validate stanza that
`_refresh_goc_validate_block` would change) and add
`and not pending_precommit_refresh` to the short-circuit guard. When the
glob is already current the flag is false and the no-op path is
unchanged.

## Why it matters

The pre-commit goc-validate hook is the consumer's frontmatter-drift
gate. A silently-dead glob means card schema violations land uncaught.
The repair exists in shipping code but is gated behind a short-circuit
that fires on the most common re-upgrade path.
