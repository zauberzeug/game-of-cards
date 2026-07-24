---
title: install-writes-pre-commit-entry-that-fails-on-plugin-only-hosts
summary: "goc install and goc upgrade unconditionally append a pre-commit stanza with 'entry: goc validate' + 'language: system', even when the install pins skills_source: plugin and never puts a goc executable on PATH (plugin mode's bin/ prepend exists only inside Claude Code's Bash tool). In any consumer repo that runs pre-commit from a normal terminal or CI, every commit fails with 'Executable goc not found' — or, where pre-commit is not wired, the advertised frontmatter-drift gate silently never runs."
status: open
stage: null
contribution: high
created: "2026-07-24T01:31:07Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra]
definition_of_done: |
  - [ ] PROCESS: entry-resolution mechanism decided (option A/B/C/D in "Decision required") and gate lowered to none
  - [ ] TDD: reproduce.py exits zero — the written stanza's entry resolves on a host whose PATH lacks a bare `goc` (or install explicitly warns/skips when it cannot)
  - [ ] TDD: regression test covers the plugin-default install path: the written .pre-commit-config.yaml entry must be executable without a pipx/global goc install
  - [ ] MECHANICAL: `_migrate_precommit_validate_pattern` / `_precommit_hook_drifted` migrate existing consumer stanzas to the chosen entry on `goc upgrade`
  - [ ] MECHANICAL: plugin mirrors resynced (claude-plugin/goc, codex-plugin/goc, openclaw-plugin/goc pick up install.py automatically via sync)
---

# Installed pre-commit `goc validate` hook fails every commit on plugin-only hosts

## Location

- `goc/install.py:64-73` — the stanza template:

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

- `goc/install.py:1322` — `_append_precommit_hook`, called unconditionally
  for git repos at `goc/install.py:1576` (install) and `goc/install.py:1823`
  (upgrade). No `_is_plugin_context()` / `skills_source` gate, no check that
  any PATH-resolvable `goc` will exist on the host.

## What's broken

The *default* Claude install path is plugin mode: `_should_use_local_skills`
defaults Claude to plugin, install pins `skills_source: plugin`, and the
project docs advertise "Python 3.10+ is the only host prerequisite" — the
plugin's `bin/goc` wrapper is prepended to PATH **only inside Claude Code's
Bash tool** while the plugin is enabled. There is no `goc` on the host's
normal PATH, by design.

Yet the same install writes a pre-commit hook with `language: system` and
`entry: goc validate`, which pre-commit resolves via plain PATH lookup. So
in any consumer repo that wires pre-commit and commits from a terminal,
IDE, or CI:

```
goc validate.............................................................Failed
- hook id: goc-validate
- exit code: 1

Executable `goc` not found
```

Every commit fails until the user hand-edits the stanza or installs
`game-of-cards` globally — a prerequisite the plugin path explicitly
promises they don't need. Where pre-commit is *not* wired as a git hook,
the failure inverts into silence: the advertised frontmatter-drift gate
never runs at all.

Smoking gun in this very repo: the dogfood `.pre-commit-config.yaml` had to
be hand-diverged to `entry: uv run goc validate` because bare `goc` is not
on PATH here either.

## Empirical evidence

`reproduce.py` (sibling file, offline) scaffolds a throwaway git repo, runs
the in-repo engine's `install --agents claude`, and shows the written entry
cannot resolve on a PATH without a global `goc`:

```
[1] install pinned skills_source: plugin
[2] written .pre-commit-config.yaml entry: 'goc validate' (language: system)
[3] PATH used by pre-commit lookup has no 'goc': shutil.which -> None
[FAIL] plugin-default install wrote a pre-commit entry that cannot execute on this host
```

Verified live 2026-07-24 with real pre-commit in `/tmp/audit-probe`:
`uvx pre-commit run --all-files` → `goc validate ... Failed / Executable
`goc` not found` (output above quoted verbatim).

## Why it matters

Reachability: `goc install` (any agent set, default flags) in a git repo →
`_append_precommit_hook` → stanza written; first `git commit` in a repo
with pre-commit wired → hard failure. This is the default onboarding path,
not an edge case. The closed card
[skill-preamble-shell-blocks-call-bare-goc-and-abort-skill-load-off-path](../skill-preamble-shell-blocks-call-bare-goc-and-abort-skill-load-off-path/)
fixed the same off-PATH resolution class for skill `!` blocks via
`_goc-bootstrap.sh`, but its fix deliberately did not touch the pre-commit
template — this card is the remaining surface.

## Decision required

Which entry should the stanza ship (and should install gate/warn)?

- **Option A — bootstrap-style resolver entry.** Ship a small resolver
  (mirroring `_goc-bootstrap.sh`: PATH goc → plugin bin → `uv run goc`)
  and point `entry:` at it. Most robust; adds a file consumers must keep.
- **Option B — `entry: python3 -m goc.cli validate` with PYTHONPATH set to
  a discovered plugin root.** No extra file, but the plugin root path is
  machine-specific — awkward to bake into a committed config.
- **Option C — gate the append on install mode.** Plugin-mode installs skip
  the stanza (or write it commented-out) and print a note that the drift
  gate requires a pipx install; vendored/pipx installs keep today's entry.
  Simplest, but plugin consumers lose the automated gate.
- **Option D — keep the entry, add an install-time warning** when no
  PATH-resolvable `goc` exists ("pre-commit hook written; requires `pipx
  install game-of-cards`"). Cheapest; every commit still fails until the
  user acts.

Whichever option lands, `goc upgrade` must migrate the already-written
stanza in existing consumer repos (the `_precommit_hook_drifted` /
`_migrate_precommit_validate_pattern` machinery already exists for the
`files:` glob migration).
