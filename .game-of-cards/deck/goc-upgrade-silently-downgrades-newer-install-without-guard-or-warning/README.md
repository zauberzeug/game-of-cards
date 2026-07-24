---
title: goc-upgrade-silently-downgrades-newer-install-without-guard-or-warning
summary: "upgrade()'s only version comparison is the equality short-circuit (existing == __version__); there is no ordering check anywhere, so an older engine running goc upgrade in a repo stamped by a newer release regresses vendored skills/hooks (rmtree + recopy of the older templates) and rewrites .goc-version downward — exit 0, 'upgrade complete — 9.9.9 → 0.0.27', no warning or prompt. Realistic reach: plugin payload pins routinely lag the pipx install."
status: open
stage: null
contribution: medium
created: "2026-07-24T01:09:58Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] TDD: a committed `reproduce.py` scaffolds an installed repo, overwrites `.goc-version` with `9.9.9`, runs the current engine's `goc upgrade` non-interactively, and shows exit 0 + `9.9.9 → ` in stdout + the sentinel regressed with no warning token — drop the `unverified` tag when it lands.
  - [ ] MECHANICAL: the chosen guard (see `## Decision required`) lands in `goc/install.py`'s `upgrade()`.
  - [ ] TDD: a regression test covers the downgrade path (refusal, warning, or flag — per the decision) and the suite passes.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# goc upgrade silently downgrades a newer install without guard or warning

## Summary

`upgrade()` never checks the *direction* of the version change. An engine
older than the repo's stamped `.goc-version` happily "upgrades" the repo
downward: vendored skills and hooks are replaced with the older engine's
templates and the sentinel is rewritten to the lower version, with a
success message and no warning.

## Location

- `goc/install.py:1754-1765` — the only version comparison in `upgrade()`
  is equality:

  ```python
  if (
      existing == __version__
      and not dry_run
      ...
  ):
      print(f"already at goc {__version__} — nothing to do.")
  ```

  No `existing > __version__` (or any ordering) check exists anywhere in
  the function.

- `goc/install.py:1807-1810` — for vendored agents the sync runs with
  `replace = agent in local_skills_agents` →
  `_sync_agent_harness(..., replace_skills=replace)`, and `_sync_skill_tree`
  (`goc/install.py:1224-1228`) `shutil.rmtree`s each eligible skill dir
  before recopying — newer vendored skills/hooks are replaced by the older
  engine's templates.
- `goc/install.py:1825` — `(deck_dir / ".goc-version").write_text(__version__
  + "\n")` regresses the sentinel.

## What's broken

"Upgrade" is directional by name and by every message it prints, but the
implementation is "sync to whatever version I am". The user-owned content
guarantees still hold (authored `.game-of-cards/` files are preserved), yet
the goc-owned surfaces — vendored skills, hooks, the AGENTS.md marker block,
the sentinel — all silently regress to the older engine's payload.

## Evidence (unverified — no committed reproduce.py yet)

A hunter agent set `.game-of-cards/deck/.goc-version` to `9.9.9` in a
scratch repo and ran the 0.0.27 engine's `goc upgrade`: it completed with
`goc upgrade complete for agents: claude — 9.9.9 → 0.0.27.` and the sentinel
then read `0.0.27`. No warning, no prompt.

Falsification recipe: repeat that run; the defect is disproved if upgrade
refuses, prompts, or prints any downgrade warning before rewriting the
sentinel.

## Why it matters

Stale engines running `upgrade` against newer-stamped repos is the expected
skew direction: the plugin payload pins routinely lag the pipx/pip install —
the repo's own marketplace-pin-check workflow exists precisely because pins
drift behind releases (see
[zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases](../zauberzeug-claude-marketplace-pin-drifts-silently-behind-releases/)).
It composes badly with
[vendored-engine-reports-co-installed-distribution-version-not-its-own](../vendored-engine-reports-co-installed-distribution-version-not-its-own/),
which can make the *direction* of the skew invisible to the engine itself.
Reachability path: consumer repo maintained with a newer CLI → older plugin
or pip engine runs `goc upgrade` (or the `Skill(upgrade)` flow) → silent
template/sentinel regression.

## Decision required

1. **Refuse downgrades.** If `existing` parses as a version greater than
   `__version__`, exit 1 with an explanation and a `--force` escape hatch.
2. **Warn + confirm.** Print a downgrade warning and require interactive
   confirmation (or `--force` in non-TTY contexts); proceed otherwise.
3. **Intentional bidirectional sync.** Keep behavior but rename the
   messaging (say "sync", state the direction explicitly) so the output
   never claims an upgrade while downgrading.

A wrinkle for options 1–2: `.goc-version` values are not guaranteed to be
PEP 440-parseable (the sentinel is a free-text stamp), so the ordering
check needs a defined fallback for unparseable values.
