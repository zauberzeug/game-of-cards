---
title: goc-upgrade-leaves-stale-pre-commit-validate-pattern
status: active
stage: null
contribution: medium
created: "2026-06-24T08:31:29Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
summary: "goc upgrade no-ops the pre-commit goc-validate hook whenever its block already exists, so a repo installed before the deck moved from deck/ to .game-of-cards/deck/ keeps the legacy `files: ^deck/.*$` glob. The hook then matches no real card path and the frontmatter-drift gate is silently dead."
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (a legacy `files: ^deck/.*$` block is rewritten to the current `.game-of-cards/deck` pattern on upgrade)
  - [ ] TDD: regression test in tests/ asserts an upgrade over a legacy-pattern config lands the current `files:` glob, and that an already-current block is left byte-identical (idempotent no-op preserved)
  - [ ] MECHANICAL: a non-GoC `repo: local` hook or a user-authored hook elsewhere in the file is preserved untouched
worker: {who: "claude[bot]", where: main}
---

# goc-upgrade-leaves-stale-pre-commit-validate-pattern

## Location

`goc/install.py` — `_append_precommit_hook` (the short-circuit `if "id: goc-validate" in text: return`).

## What's broken

`_append_precommit_hook` writes the `goc-validate` pre-commit hook, whose
`files:` glob is pinned in the module-level `PRE_COMMIT_HOOK` constant:

```python
PRE_COMMIT_HOOK = """\
  - repo: local
    hooks:
      - id: goc-validate
        name: goc validate
        entry: goc validate
        language: system
        pass_filenames: false
        files: ^\\.game-of-cards/deck/.*$
"""
```

Commit `9fa3a24` ("deck: move canonical deck from deck/ to .game-of-cards/deck")
moved the deck and updated this glob from the legacy `^deck/.*$` to
`^\.game-of-cards/deck/.*$`. Any repo that ran `goc install` **before** that
move has a `.pre-commit-config.yaml` containing the legacy `files: ^deck/.*$`.

`goc upgrade` calls `_append_precommit_hook` (`install.py:1743`) precisely to
"sync template updates", but the function short-circuits:

```python
    text, newline = _read_text_keep_newline(target)
    if "id: goc-validate" in text:
        return
```

Because the `id: goc-validate` line is still present, the function returns
without touching the stale `files:` line. The legacy glob is never migrated to
the new deck path.

## Why it matters

pre-commit's `files:` regex now matches a path (`deck/...`) that no longer
exists on disk, so the `goc-validate` hook **never triggers** on edits to cards
under `.game-of-cards/deck/`. AGENTS.md calls this frontmatter-drift gate
"load-bearing"; for every pre-move install it is silently dead at commit time,
and `goc upgrade` — the one command whose job is to carry template fixes
forward — does not repair it.

Reachability: the offending input is produced by `goc install` itself at any
version prior to `9fa3a24`. The consumer flow is `goc upgrade →
_append_precommit_hook → no-op`.

## Empirical evidence

`reproduce.py` seeds a `.pre-commit-config.yaml` whose `goc-validate` block
carries the legacy `files: ^deck/.*$`, calls `_append_precommit_hook`, and
checks the result:

```
CHANGED: False
still legacy ^deck/: True
has new .game-of-cards/deck: False
```

Correct behavior: the GoC-managed block's `files:` line should be rewritten to
`^\.game-of-cards/deck/.*$` so the hook matches real card paths again.

## Fix

In `_append_precommit_hook`, when a `goc-validate` block is already present but
its body differs from the current `PRE_COMMIT_HOOK`, re-emit the GoC-managed
block in place (replace the existing `- repo: local … id: goc-validate …`
stanza) rather than returning a no-op. Match only the GoC-managed stanza so
unrelated `repo: local` hooks and user-authored hooks elsewhere in the file are
preserved. An already-current block stays a byte-identical no-op.
