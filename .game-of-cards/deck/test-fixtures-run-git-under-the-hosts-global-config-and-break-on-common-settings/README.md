---
title: test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings
summary: "No test module isolates git from the host's global config, so every git process the suite starts, in a fixture or through goc's own auto-commit, reads the .gitconfig of whoever runs it. On an unchanged tree two common settings each break the suite: commit signing with an unavailable key (54 errors in 16 modules) and a refusing global pre-commit hook (55 errors in 17 modules). A third, safe.bareRepository=explicit (2 errors, in every bot session), was fixed on 2026-11-16 by its instance card. Two modules already guard against signing on their own, and a 2026-05 closure ran the suite with GIT_CONFIG_GLOBAL=/dev/null to get past a host-identity leak. One shared isolation would end these per-module fixes."
status: active
stage: null
contribution: medium
created: "2026-11-16T01:13:32Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories
tags: [bug, test, infra, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits 0. Under each host config it tries (the bare-repository hardening, signing with an unavailable key, a refusing global pre-commit hook), the full suite gives the control's result. Today each of the three gives `Ran 1492 tests` and `FAILED`, against `Ran 1499 tests` and `OK`.
  - [ ] MECHANICAL: one shared mechanism keeps every git process the suite starts, in fixtures and through goc subprocesses, off the host's global and system git config. It is not a per-module flag. The per-module `commit.gpgsign false` lines (`tests/test_refine_deck_stale_parks.py:148`, `tests/test_project_root_from_subdirectory.py:87`) are folded into it or shown to be redundant.
  - [ ] TDD: a guard fails in CI when a test module starts git outside that isolation. It is shown to catch a planted offender before the fix lands, and it costs far less than another full-suite run.
  - [ ] MECHANICAL: the AGENTS.md paragraph on `tests/` says the suite runs git isolated from the host's git config, so a new fixture author knows the contract.
  - [ ] PROCESS: every instance card wired into `advanced_by` is closed, and `uv run python -m unittest discover -s tests` and `uv run goc validate` pass.
worker: {who: "claude[bot]", where: main}
---

# Test fixtures run git under the host's global config and break on common settings

About half the test modules start git, either directly to build a fixture
repository or through a goc verb that auto-commits: 96 of 180 match a grep
for git and goc subprocess calls. None of them gives git a config of its own. Each git process reads the global `.gitconfig` (and the
system config) of whoever runs the suite. A host setting that makes git refuse
an operation the fixtures rely on therefore turns the suite red with no change
to goc. Three common settings do so today. Each new way a host differs gets
patched in whichever module noticed it, or worked around at the command line.

## Location

There is no single site. The family is the absence of a shared isolation
step:

- No module, helper or entry point sets up a git config for the suite.
  `python -m unittest discover -s tests` imports the modules as top-level
  names, so nothing runs before them that could do it for the whole process.
- Four modules build their subprocess env by dropping every `GIT_*` variable
  (`tests/test_claim_race_reassurance.py:115`,
  `tests/test_claude_settings_hook_edit_claims.py:86`,
  `tests/test_deck_location_claim_rows.py:109`,
  `tests/test_plugin_payload_dependency_manifests.py:115`). That keeps a
  caller's `GIT_DIR` out, but it also strips `GIT_CONFIG_GLOBAL` and
  `GIT_CONFIG_NOSYSTEM`, so a caller cannot isolate those modules from
  outside.
- Per-module guards against one setting at a time: two fixtures turn off
  signing in their own repo (`tests/test_refine_deck_stale_parks.py:148`,
  `tests/test_project_root_from_subdirectory.py:87`:
  `self.git(..., "config", "commit.gpgsign", "false")`). The first still fails
  under a global hooks directory. Five modules point HOME elsewhere, each for
  its own reason (worker auto-population, plugin detection, a pinned PATH):
  `tests/test_auto_populate_worker_empty_who.py:81`,
  `tests/test_auto_populate_worker_preserves_where.py:60`,
  `tests/test_claude_settings_hook_edit_claims.py:89`,
  `tests/test_standup_next_up_row_budget.py:118`,
  `tests/test_plugin_present_detection.py:48`.

## Instances

| Host setting | Effect on the suite | Where seen | Card |
|---|---|---|---|
| a long global `user.name` | it widened the worker label on the board, which clipped the slug a board test read | a local run, 2026-05 | noted in [test-move-asserts-old-inline-advances-format](../test-move-asserts-old-inline-advances-format/) § Notes and resolved through the board renderer by [board-active-card-worker-label-not-truncated](../board-active-card-worker-label-not-truncated/), not through test isolation |
| global identity (same class) | one environment-sensitive board test failed, so the suite was run as `env GIT_CONFIG_GLOBAL=/dev/null uv run pytest` | closure log of [half-edge-repair-requires-manual-multi-file-edits](../half-edge-repair-requires-manual-multi-file-edits/), 2026-05-18 | none filed |
| `safe.bareRepository = explicit` | 2 `setUpClass` errors; 7 tests never run | every autonomous session since `anthropics/claude-code-action@v1` began writing it (first seen 2026-11-16) | [regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories](../regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories/) (advances this card; closed 2026-11-16, the remote named with `--git-dir`) |
| `commit.gpgsign = true` with a key that is not available | 54 errors in 16 modules: each fixture's own `git commit … check=True` raises (`error: gpg failed to sign the data`) | reproduced here | this card |
| `core.hooksPath` with a refusing `pre-commit` | 55 errors in 17 modules: the same fixture commits, refused by the hook | reproduced here | this card |

Settings tried that did **not** change the result (full suite, 1499 tests,
`OK` under each): a long `user.name`, `init.defaultBranch = trunk`,
`pull.ff = only`, `core.autocrlf = true`, `user.useConfigOnly = true`. The
fixtures pass `-b main` and set an identity, so the family is the settings
that make git *refuse*, not the ones that change its output.

The modules hit by signing and by hooks are the same 16, plus
`test_refine_deck_stale_parks` under hooks. The largest is
`test_refine_deck_citation_anchor` (28 errors); the others include
`test_release_verbs_restore_a_lost_created_stamp` (5),
`test_auto_commit_stdout_isolation` (4), `test_draft_auto_commit_excluded`
(3), `test_new_wires_edges` (2), `test_install` (2) and
`test_git_auto_commit_pathspec`, `test_git_auto_commit_rebase_guard`,
`test_move_rewrites_untracked_card`, `test_move_shared_worktree_git_cwd`,
`test_migrate_shared_worktree_tree_resolution`,
`test_new_resolves_existing_deck_root`,
`test_new_shared_worktree_path_display`,
`test_decide_releases_parked_active_claim`, `test_claim_race_reassurance` and
`test_deck_location_claim_rows` (1 each).

## Empirical evidence

`reproduce.py` runs the full suite once per global git config, all four in
parallel, each with its own HOME and XDG_CONFIG_HOME so the only global
config is one the script wrote. It takes about two minutes. Output on
2026-11-16 (`main` at `ada1d2e7`, git 2.56, Python 3.12):

```
git 2.56
full suite (`python -m unittest discover -s tests`), one run per global git config

control     ran 1499, OK
bare-repos  ran 1492, FAILED (errors=2)  [CHANGED]
              2 module(s) with errors or failures: test_claim_race_reassurance, test_deck_location_claim_rows
signing     ran 1492, FAILED (errors=54)  [CHANGED]
              16 module(s) with errors or failures: test_auto_commit_stdout_isolation, test_claim_race_reassurance, test_decide_releases_parked_active_claim, test_deck_location_claim_rows, test_draft_auto_commit_excluded, test_git_auto_commit_pathspec, +10 more
hooks       ran 1492, FAILED (errors=55)  [CHANGED]
              17 module(s) with errors or failures: test_auto_commit_stdout_isolation, test_claim_race_reassurance, test_decide_releases_parked_active_claim, test_deck_location_claim_rows, test_draft_auto_commit_excluded, test_git_auto_commit_pathspec, +11 more

DEFECT: 3 of 3 host git config(s) change the suite's result (bare-repos, signing, hooks). The fixtures inherit the host's global git config.
```

It exits 1. It exits 0 once every config gives the control's result, and 2
when the control itself fails or git is older than 2.38.

## Why it matters

- **A red suite that is not about goc.** A contributor who signs commits, or
  works under an organisation's global hooks, clones the repo and sees 54 or
  55 errors before changing anything. All of them are errors, not failures:
  fixtures' own setup commits raise, and the tests behind them never run. A
  real regression in those 16 or 17 modules would be invisible on that
  machine.
- **A common way to hit the signing row.** Some dev containers and sandboxes
  copy the host `.gitconfig` without the key agent it names.
- **Bot sessions already hit it.** The bare-repository instance was live in
  every autonomous workflow run until its own card fixed it on 2026-11-16,
  and there the bot's own suite run is the only gate on its commits
  ([autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing](../autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/)).
- **Per-module fixes do not converge.** Each instance so far was handled
  where it showed up: a `commit.gpgsign false` in two fixtures, a board
  rendering change, a `GIT_CONFIG_GLOBAL=/dev/null` prefix in one closer's
  command line. The next fixture written without that knowledge reopens the
  family. The guard that would stop it does not exist.

## Fix

Give the suite one git environment of its own and route every git process
through it:

- A shared helper (a module under `tests/` whose name does not match
  `test*.py`, imported by every module that starts git) sets, once per
  process, `HOME` and `XDG_CONFIG_HOME` to a temporary directory. That
  directory holds a minimal `.gitconfig` (identity only), and the helper sets
  `GIT_CONFIG_NOSYSTEM=1`. Pointing HOME elsewhere survives the four `_env()`
  helpers that strip `GIT_*` variables. Those helpers should keep
  `GIT_CONFIG_NOSYSTEM` (or the helper should supply it) so the system config
  stays out too.
- The modules that already point HOME elsewhere for their own reasons keep
  doing so. Each must still end up with an isolated git config, which the
  guard checks.
- The guard should not cost another full-suite run. One option is a static
  check that every module which starts git imports the helper, plus one small
  dynamic test showing the helper neutralises a hostile global config (signing
  on, a refusing hook, `safe.bareRepository = explicit`). Another is a single
  run of the git-touching modules under that combined hostile config.

This does not replace the bare-repository instance's own fix. Isolation would
stop the action's setting from reaching the tests, but that card's `--git-dir`
edits are correct either way. Its guard,
`tests/test_bare_repository_fixtures_name_their_git_dir.py`, deliberately runs
the bare-remote fixtures *under* the hardened config, and the two closed
cards' reproducers it repaired are not part of the suite at all. The guard
also fails a module after whose import git no longer sees
`safe.bareRepository = explicit`. The helper above sets HOME on import, so its
minimal `.gitconfig` has to set `safe.bareRepository = explicit` too, which
also keeps the whole suite under the setting every bot session runs with.
Without it the guard turns red on both bare-remote modules.

Deck reproducers have the same exposure but are out of scope here. They are
records, run one at a time, and each can pin its own HOME, as this card's and
the bare-repository card's do.
