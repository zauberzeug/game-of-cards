---
title: regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories
summary: "Two regression-test classes, and the reproducers of the two closed cards that added them, read a scratch bare remote by running git inside it, and git refuses that when the global config sets safe.bareRepository=explicit, which anthropics/claude-code-action@v1 writes before every Claude session. So in every pull-card, refine-deck and audit-deck run the suite reports FAILED (errors=2) with 1492 tests run instead of 1499 OK, the 7 claim-race doc guards never execute, and the 55 live cards whose DoD says the suite passes cannot be closed honestly by a bot. Naming the remote with --git-dir at the 11 call sites fixes all four."
status: open
stage: null
contribution: high
created: "2026-11-16T00:52:01Z"
closed_at: null
human_gate: none
advances:
  - test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings
advanced_by: []
tags: [bug, infra, test]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits 0. Every `tests/` module that creates a bare repository, and both closed-card reproducers it runs, give the same result under an empty global git config and under `safe.bareRepository = explicit`. It exits 1 today, with 4 of 4 targets diverging.
  - [ ] MECHANICAL: all 11 git calls that run inside a bare remote name it explicitly with `--git-dir` (or read it through a clone): `tests/test_claim_race_reassurance.py:149,156`, `tests/test_deck_location_claim_rows.py:169,172,178`, and the `reproduce.py` of the two closed cards under Location (`:114,148,151,157,160` and `:123`). Each closed card gets a `log.md` post-close amendment that names the edit and points here. Nothing opts out with `-c safe.bareRepository=all`.
  - [ ] TDD: a new test runs every `tests/` module that creates a bare repository under a HOME whose `.gitconfig` sets `safe.bareRepository = explicit`, and asserts each module runs all its tests and passes. It fails on today's fixtures before they are fixed (record that run in log.md), so the next fixture that runs git inside a bare repository turns CI red and not only bot sessions.
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` passes with the same test count under the session's own git config and with HOME pointed at an empty `.gitconfig` (both counts recorded in log.md), and `uv run goc validate` passes.
---

# The regression suite is red inside every bot run: two fixtures open a bare repository that git refuses to find

Every autonomous workflow in this repo runs `anthropics/claude-code-action@v1`.
That action now sets `safe.bareRepository = explicit` in the global git config
before each Claude session. Two test classes, and the reproducers of the two
closed cards that added them, run `git` with a scratch bare remote as the
working directory. Under that setting git refuses to find a bare repository
that way. So both classes error out in `setUpClass`, their 7 tests never run,
and the suite a bot runs to tick its DoD reports `FAILED (errors=2)`.

## Location

- `tests/test_claim_race_reassurance.py:149` and `:156`:
  `_git(remote, "rev-parse", "main")`, run with the bare repository created at
  `:137` as `cwd`. Called from `setUpClass` (`:209`) of
  `ClaimRaceReassuranceTest`, which holds 4 tests.
- `tests/test_deck_location_claim_rows.py:169`, `:172` and `:178`: two
  `_git(remote, "rev-parse", "main")` calls and one `_git(remote, "show", …)`,
  with the bare remote created at `:135`. Called from `setUpClass` (`:249`) of
  `DeckLocationClaimRowsTest`, which holds 3 tests.
- The helpers both modules share in shape: `_git`
  (`tests/test_claim_race_reassurance.py:120`,
  `tests/test_deck_location_claim_rows.py:115`) runs `git` with the given
  directory as `cwd` and no `--git-dir`. `_env` (`:113` / `:107`) drops every
  `GIT_*` variable, so a `GIT_DIR` or `GIT_CONFIG_GLOBAL` set by the caller
  never reaches git.
- The same helper shape in two closed cards' reproducers:
  - [deck-location-doc-says-claims-push-by-default-and-last-writer-wins](../deck-location-doc-says-claims-push-by-default-and-last-writer-wins/)
    `reproduce.py:114`, `:148`, `:151`, `:157`, `:160`
  - [deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects](../deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects/)
    `reproduce.py:123`
- Where the setting comes from: `prepareGitForSession` in the action's
  `src/github/operations/session-guard.ts`, which runs
  `setConfig("--global", [["safe.bareRepository", "explicit"]])`. The action's
  `src/entrypoints/run.ts` calls it before every session, with no condition.
  The behavior is documented in its `docs/security.md` § "What a session can
  leave behind". The workflows that run the action:
  `.github/workflows/pull-card.yml:80`, `refine-deck.yml:52`,
  `audit-deck.yml:50`, plus `claude.yml`, `claude-code-review.yml` and
  `release.yml`.

## What's broken

The fixture seeds a bare remote, then reads it by running git inside it
(`tests/test_claim_race_reassurance.py:120-123`, `:136-149`):

```python
def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=_env(), check=True, capture_output=True, text=True
    ).stdout.strip()
...
    remote = work / "remote.git"
    _git(work, "init", "-q", "--bare", "-b", "main", str(remote))
    ...
    before = _git(remote, "rev-parse", "main")
```

That is implicit discovery: git finds the repository from the working
directory. With `safe.bareRepository = explicit`, git accepts a bare
repository only when the caller names it (`--git-dir` or `GIT_DIR`).
Otherwise it stops with:

```
fatal: cannot use bare repository '/tmp/…/remote.git' (safe.bareRepository is 'explicit')
```

The clone, commit and push steps before it still work, because a transport
names the remote directory itself. Only the reads that run inside the remote
fail. They fail in `setUpClass`, so none of the class's tests is counted as
run.

The action documents the requirement (`docs/security.md`, § "What a session
can leave behind"):

> Global git config also sets `safe.bareRepository=explicit` for the session,
> so git won't use a repository it finds in a folder that has no `.git`. A
> workflow that has Claude work in a bare repository needs to pass
> `--git-dir`.

AGENTS.md describes the suite as one command that passes wherever it runs,
and names it the gate for code correctness:

> `tests/` is a stdlib `unittest`-based regression suite (run it locally
> with `uv run python -m unittest discover -s tests`; it also passes under
> pytest). […] the `Run regression tests` step (`uv run python -m unittest
> discover -s tests`) gates code correctness

Nothing else is affected:

- These two are the only modules under `tests/` that create a bare
  repository.
- Under `goc/`, git runs only in the deck's working tree, never inside a bare
  remote. The sweep did turn up an unrelated bare-repository problem in
  shipped code, parked as
  [shared-worktree-deck-finds-no-deck-when-the-repository-is-a-bare-clone](../shared-worktree-deck-finds-no-deck-when-the-repository-is-a-bare-clone/).
- `scripts/` and `.github/` create no bare repository.
- Three open cards' reproducers also use a bare remote:
  `claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset`,
  `claim-push-reports-success-when-rebase-drops-identical-racing-claim` and
  `closure-on-integration-check-silently-skips-on-non-origin-main-repos`.
  None of them runs git inside the remote, and each printed the same exit
  code and verdict under both configs.

## Empirical evidence

`reproduce.py` runs each target twice. Each run gets its own HOME and
XDG_CONFIG_HOME, so the only global git config is one the script wrote. In
the control run that file is empty. In the hardened run it holds
`[safe] bareRepository = explicit`, which is what the action writes. The
targets are found by content: every `tests/` module containing `--bare`, plus
the two closed-card reproducers. Output on 2026-11-16, git 2.56:

```
git 2.56; safe.bareRepository is honored from 2.38
global git config: control = empty; hardened = `[safe] bareRepository = explicit`

tests.test_claim_race_reassurance                              [DIVERGES]
                                                                 control:  ran 4, OK
                                                                 hardened: ran 0, FAILED (errors=1)
tests.test_deck_location_claim_rows                            [DIVERGES]
                                                                 control:  ran 3, OK
                                                                 hardened: ran 0, FAILED (errors=1)
deck/deck-location-doc-says-claims-push-by-de.../reproduce.py  [DIVERGES]
                                                                 control:  exit 0: Both rows match the observed claim protocol.
                                                                 hardened: exit 1: subprocess.CalledProcessError: Command '['git', 'rev-parse', 'main'...
deck/deck-skill-promises-git-merge-settles-cl.../reproduce.py  [DIVERGES]
                                                                 control:  exit 0: No surface says git's merge settles the race.
                                                                 hardened: exit 1: git show main:.game-of-cards/deck/race-card/README.md failed: fatal...

DEFECT: 4 of 4 target(s) pass with an empty global git config and fail under the setting claude-code-action@v1 writes for every session.
```

It exits 1. In a scratch clone where `"--git-dir=.",` is added to the 11
`_git(remote, …)` calls, it exits 0, with `ran 4, OK`, `ran 3, OK`, `exit 0`
and `exit 0` under both configs. Exit 2 means nothing could be measured: git
is older than 2.38, a target is missing, or a control run fails by itself.

The full suite, 2026-11-16, Python 3.12:

| tree | global git config | result |
|---|---|---|
| `main` at `ada1d2e7` | the one this audit-deck session ran with (the action's) | `Ran 1492 tests`, `FAILED (errors=2)` |
| `main` at `ada1d2e7` | empty (HOME pointed at a scratch dir) | `Ran 1499 tests`, `OK` |
| scratch fix (the 11 `--git-dir=.` edits) | `safe.bareRepository = explicit` | `Ran 1499 tests`, `OK` |

Both errors are `setUpClass` errors: `git rev-parse main` exits 128.

## Why it matters

This card is one instance of
[test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings](../test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings/)
and advances it. Commit signing and global hooks break the same suite the
same way. This instance is the one live in every bot session, so it is filed
on its own, with a fix that stays correct whatever the family fix turns out to
be.

- **A bot's own run is the only gate on the autonomous path.** Bot pushes do
  not trigger CI
  ([autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing](../autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/)),
  so what pull-card sees inside its session is the only check its commits
  get. CI does not run the action, so the failure never shows there.
- **Bots cannot close cards honestly.** 55 of the 192 live cards have a DoD
  box that runs `uv run python -m unittest discover -s tests` and requires it
  to pass, and 159 closed cards had one. `goc done` refuses unchecked boxes.
  A bot that reports the red suite faithfully cannot close any of those
  cards. A bot that ticks the box anyway does it over two errors it has to
  explain away, and that habit hides the next real failure.
- **Seven doc guards go dark where they are needed.** The skipped tests check
  that the deck skill, ABOUT.md and DECK_LOCATION.md describe the claim
  protocol the engine actually runs. Inside a session they never execute. A
  bot edit that brings back the claim that git's merge settles a claim race
  passes the bot's own run.
- **Not hit yet, only because the queue is empty.** The pull-card run that
  made closure commit `116b2643` (dispatched 2026-11-09 05:05 UTC) logged
  `Ran 1499 tests` / `OK` from inside its session, so the setting arrived
  after that. The scheduled pull-card runs of 2026-11-10 to 2026-11-15 each
  logged `Ready cards (goc --ready): 0` and skipped the agent step. This
  audit run is the first session seen with the setting. The next card that
  becomes ready will meet a red suite.
- **Closed cards' evidence crashes.** Re-run either closed card's
  `reproduce.py` inside a session and you get a traceback instead of the
  verdict the card was closed on. That happens to a closer re-verifying, or to
  refine-deck's re-check of gated cards whose cited code moved.

## Fix

Name the bare remote explicitly wherever git runs inside it, which is what
the action's docs prescribe. The smallest edit is the one the scratch check
used: `_git(remote, "--git-dir=.", "rev-parse", "main")`, and the same for
`show`, at the 11 call sites under Location. A `_remote_git(remote, *args)`
helper that passes `--git-dir=<remote>` reads better, and the next call site
cannot forget the flag.

Not the fix:

- `-c safe.bareRepository=all` on these calls. It would pass, but it turns
  off the protection the action turned on.
- Changing the workflows. The setting applies inside the session that runs
  the suite, `_env()` strips `GIT_*` overrides anyway, and AGENTS.md records
  that the bot cannot edit `.github/workflows/`.

Then add the guard from the DoD, so a new bare-remote fixture fails in CI and
not only in bot sessions. CI does not run under the action, so the guard has
to set the hardened config itself. It runs each `tests/` module that creates
a bare repository with HOME pointed at a temporary `.gitconfig` that sets
`safe.bareRepository = explicit`. It compares the run count with the
module's `countTestCases()` and requires `OK`. It leaves its own file out of
its `--bare` scan.

For the two closed cards, editing the reproducer maintains their evidence; it
does not reopen them. Record the edit in each card's `log.md` as a post-close
amendment (`Skill(finish-card)` § "After closure").
