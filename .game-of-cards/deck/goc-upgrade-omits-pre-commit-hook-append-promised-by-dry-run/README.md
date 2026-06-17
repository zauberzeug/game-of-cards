---
title: goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run
status: active
stage: null
contribution: medium
created: "2026-06-17T04:39:17Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — after a real `goc upgrade` in a git repo whose `.pre-commit-config.yaml` is absent, the file exists and contains `id: goc-validate`
  - [ ] TDD: regression test in tests/test_install.py asserts dry-run/real parity — any `append .pre-commit-config.yaml` line in the upgrade plan implies the hook is present after the real run
  - [ ] MECHANICAL: `upgrade()` calls `_append_precommit_hook(target / ".pre-commit-config.yaml")` alongside the other sync steps
  - [ ] `uv run python -m unittest discover -s tests` passes
  - [ ] `uv run goc validate` passes
worker: {who: "claude[bot]", where: main}
---

# `goc upgrade` omits the pre-commit hook append its dry-run plan promises

## Location

`goc/install.py` — `upgrade()` body (lines ~1698–1720); the missing call
mirrors `install()`'s call at `goc/install.py:1478`. The dry-run plan
emits the append via `_plan_writes` at `goc/install.py:863`.

## What's broken

`goc upgrade --dry-run` lists a planned write of the `goc validate`
pre-commit hook:

```
$ goc upgrade --keep-local-skills --dry-run
...
Guidance:
  shared append .pre-commit-config.yaml
```

That line is produced unconditionally by `_plan_writes`:

```python
863:    writes.append(PlannedWrite("shared", "append", target / ".pre-commit-config.yaml", "guidance"))
```

and `_plan_upgrade_writes` (whose docstring states the plan exists so a
dry-run "truthfully reports" what the real run does) passes it straight
through as a `guidance` write.

But the real `upgrade()` body never appends it. Its sync sequence ends:

```python
1708:    for stale in legacy_briefings_to_strip:
1709:        _strip_goc_block(target / stale)
1710:    _sync_methodology_blocks(target, templates, resolved_briefing, agents=agents)
1711:
1712:    (deck_dir / ".goc-version").write_text(__version__ + "\n")
```

There is no `_append_precommit_hook` call anywhere in `upgrade()`. The
only call site in the module is in `install()`:

```python
1478:    _append_precommit_hook(target / ".pre-commit-config.yaml")
```

So the dry-run plan and the real run disagree — a dry-run/real-run
contract violation.

## Empirical evidence

```
=== install without .git ===
ABSENT (expected, no .git)
=== git init, then dry-run upgrade plan ===
  shared append .pre-commit-config.yaml
=== real upgrade ===
.pre-commit-config.yaml STILL ABSENT after real upgrade  <-- BUG
```

(Full reproducer in `reproduce.py`.)

## Why it matters

`install()`'s `_append_precommit_hook` early-returns when the target is
not yet a git checkout (`if not (target.parent / ".git").exists():
return`, `goc/install.py:1237`). So `goc install` in a not-yet-git
directory silently skips the hook. The natural remedy — `git init` then
`goc upgrade` — *advertises* (in its dry-run plan) that it will install
the hook, but the real run never does. The `goc validate` pre-commit
gate is therefore permanently absent for that install path, and no
`goc` verb restores it (re-running `goc install` refuses with "existing
install detected — run `goc upgrade`"). Reachability: any consumer who
runs `goc install` before `git init` (or in a directory that becomes a
git repo later) hits this; the dry-run plan actively misleads them into
believing the subsequent upgrade fixed it.

This was noted in passing in the closed card
[goc-install-skips-pre-commit-hook-setup-in-git-worktrees](../goc-install-skips-pre-commit-hook-setup-in-git-worktrees/)
("`upgrade` does not re-run this step") but never filed as its own
defect.

## Fix

Add the missing idempotent call to `upgrade()`, alongside the other
sync steps (after the `_sync_methodology_blocks` call, before the
`.goc-version` write):

```python
    _sync_methodology_blocks(target, templates, resolved_briefing, agents=agents)
    _append_precommit_hook(target / ".pre-commit-config.yaml")   # match the dry-run plan

    (deck_dir / ".goc-version").write_text(__version__ + "\n")
```

`_append_precommit_hook` is already safe on upgrade: it no-ops when the
hook id `goc-validate` is already present (`goc/install.py:1243`) and
no-ops when `.git` is absent (`goc/install.py:1237`).
