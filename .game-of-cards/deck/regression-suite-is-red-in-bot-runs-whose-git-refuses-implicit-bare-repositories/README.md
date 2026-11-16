---
title: regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories
summary: "RESOLVED. Two regression-test classes, and the reproducers of the two closed cards that added them, read a scratch bare remote by running git inside it, which git refuses under safe.bareRepository=explicit, the setting anthropics/claude-code-action@v1 writes before every Claude session. So the suite every bot ran reported FAILED (errors=2) with 1492 tests run instead of 1499, and the 7 claim-race doc guards never ran. All 11 call sites now name the remote with --git-dir, and a new guard runs every tests/ module that creates a bare repository under that setting and requires all its tests to run and pass, so the next such fixture turns CI red, not only bot sessions. The suite runs 1501 tests, OK, under the hardened config and under an empty one."
status: done
stage: null
contribution: high
created: "2026-11-16T00:52:01Z"
closed_at: "2026-11-16T04:42:38Z"
human_gate: none
advances:
  - test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings
advanced_by: []
tags: [bug, infra, test]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 0. Every `tests/` module that creates a bare repository, and both closed-card reproducers it runs, give the same result under an empty global git config and under `safe.bareRepository = explicit`. It exits 1 today, with 4 of 4 targets diverging.
  - [x] MECHANICAL: all 11 git calls that run inside a bare remote name it explicitly with `--git-dir` (or read it through a clone): `tests/test_claim_race_reassurance.py:149,156`, `tests/test_deck_location_claim_rows.py:169,172,178`, and the `reproduce.py` of the two closed cards under Location (`:114,148,151,157,160` and `:123`). Each closed card gets a `log.md` post-close amendment that names the edit and points here. Nothing opts out with `-c safe.bareRepository=all`.
  - [x] TDD: a new test runs every `tests/` module that creates a bare repository under a HOME whose `.gitconfig` sets `safe.bareRepository = explicit`, and asserts each module runs all its tests and passes. It fails on today's fixtures before they are fixed (record that run in log.md), so the next fixture that runs git inside a bare repository turns CI red and not only bot sessions.
  - [x] PROCESS: `uv run python -m unittest discover -s tests` passes with the same test count under the session's own git config and with HOME pointed at an empty `.gitconfig` (both counts recorded in log.md), and `uv run goc validate` passes.
worker: {who: "claude[bot]", where: main}
---

# The regression suite is red inside every bot run: two fixtures open a bare repository that git refuses to find

Every autonomous workflow in this repo runs `anthropics/claude-code-action@v1`.
That action sets `safe.bareRepository = explicit` in the global git config
before each Claude session. Two test classes, and the reproducers of the two
closed cards that added them, ran `git` with a scratch bare remote as the
working directory. Under that setting git refuses to find a bare repository
that way. So both classes errored out in `setUpClass`, their 7 tests never
ran, and the suite a bot runs to tick its DoD reported `FAILED (errors=2)`.

## Resolution

Every git call that ran inside a scratch bare remote now names the remote
with `--git-dir`. The two test modules and the first closed card's reproducer
route those reads through a `_remote_git(remote, *args)` helper, and the
second reproducer passes the flag at its one call site. A new guard,
`tests/test_bare_repository_fixtures_name_their_git_dir.py`, runs every other
`tests/` module that creates a bare repository under a HOME whose
`.gitconfig` sets `safe.bareRepository = explicit`, and requires each to run
every test it defines and pass. CI does not run under the action, so the
guard brings the setting there: the next fixture that runs git inside a bare
repository turns CI red, not only bot sessions. The suite runs 1501 tests,
OK, under this session's hardened config and under an empty one.

Commit signing and global hooks still break the suite on hosts that set them.
That family stays open as
[test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings](../test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings/).
Its planned fix gives git a config of its own on import. The guard fails any
module after whose import git no longer sees `safe.bareRepository =
explicit`, so that config has to carry the setting, or the guard turns red
instead of passing on nothing.

## Location

Line numbers are as filed, at `ada1d2e7`; the fix moved them.

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

## What was broken

The fixture seeded a bare remote, then read it by running git inside it
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

The clone, commit and push steps before it still worked, because a transport
names the remote directory itself. Only the reads that ran inside the remote
failed. They failed in `setUpClass`, so none of the class's tests was counted
as run.

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

Nothing else was affected:

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
the two closed-card reproducers. As filed, on 2026-11-16 with git 2.56, it
exited 1:

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

After the fix it exits 0. Its content scan now also finds the new guard,
which sets its own HOME and so behaves the same under both configs:

```
tests.test_bare_repository_fixtures_name_their_git_dir         [same]
                                                                 control:  ran 2, OK
                                                                 hardened: ran 2, OK
tests.test_claim_race_reassurance                              [same]
                                                                 control:  ran 4, OK
                                                                 hardened: ran 4, OK
tests.test_deck_location_claim_rows                            [same]
                                                                 control:  ran 3, OK
                                                                 hardened: ran 3, OK
deck/deck-location-doc-says-claims-push-by-de.../reproduce.py  [same]
                                                                 control:  exit 0: Both rows match the observed claim protocol.
                                                                 hardened: exit 0: Both rows match the observed claim protocol.
deck/deck-skill-promises-git-merge-settles-cl.../reproduce.py  [same]
                                                                 control:  exit 0: No surface says git's merge settles the race.
                                                                 hardened: exit 0: No surface says git's merge settles the race.

Fixed: all 5 target(s) behave the same under both global git configs.
```

Exit 2 means nothing could be measured: git is older than 2.38, a target is
missing, or a control run fails by itself.

The full suite, 2026-11-16, Python 3.12:

| tree | global git config | result |
|---|---|---|
| `main` at `ada1d2e7` | the filing audit-deck session's (the action's) | `Ran 1492 tests`, `FAILED (errors=2)` |
| `main` at `ada1d2e7` | empty (HOME pointed at a scratch dir) | `Ran 1499 tests`, `OK` |
| the fix | the closing pull-card session's (the action's) | `Ran 1501 tests`, `OK` |
| the fix | empty (HOME pointed at a scratch dir) | `Ran 1501 tests`, `OK` |

Both errors were `setUpClass` errors: `git rev-parse main` exits 128. The
two extra tests are the guard's. Run against the unfixed fixtures, the guard
failed with `ran 0 of 4 tests, FAILED` for `test_claim_race_reassurance` and
`ran 0 of 3 tests, FAILED` for `test_deck_location_claim_rows` (`log.md`).

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
- **Seven doc guards went dark where they are needed.** The skipped tests check
  that the deck skill, ABOUT.md and DECK_LOCATION.md describe the claim
  protocol the engine actually runs. Inside a session they never executed. A
  bot edit that brought back the claim that git's merge settles a claim race
  would have passed the bot's own run.
- **Not hit earlier, only because the queue was empty.** The pull-card run
  that made closure commit `116b2643` (dispatched 2026-11-09 05:05 UTC)
  logged `Ran 1499 tests` / `OK` from inside its session, so the setting
  arrived after that. The scheduled pull-card runs of 2026-11-10 to
  2026-11-15 each logged `Ready cards (goc --ready): 0` and skipped the agent
  step. The filing audit run was the first session seen with the setting, and
  this card was the next one pulled: its own session met the red suite.
- **Closed cards' evidence crashes.** Re-run either closed card's
  `reproduce.py` inside a session and you get a traceback instead of the
  verdict the card was closed on. That happens to a closer re-verifying, or to
  refine-deck's re-check of gated cards whose cited code moved.

## Fix

Applied 2026-11-16; the runs are in `log.md`.

1. **Named the bare remote at all 11 call sites**, which is what the action's
   docs prescribe. `tests/test_claim_race_reassurance.py`,
   `tests/test_deck_location_claim_rows.py` and the reproducer of
   [deck-location-doc-says-claims-push-by-default-and-last-writer-wins](../deck-location-doc-says-claims-push-by-default-and-last-writer-wins/)
   each got a `_remote_git(remote, *args)` helper that passes
   `--git-dir=<remote>`, so the next read there cannot forget the flag. Their
   `rev-parse main` and `show` reads go through it. The reproducer of
   [deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects](../deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects/)
   passes the flag at its one call site. Nothing opts out with
   `-c safe.bareRepository=all`, which would turn off the protection the
   action turned on.
2. **Added the guard**, `tests/test_bare_repository_fixtures_name_their_git_dir.py`,
   so a new bare-remote fixture fails in CI and not only in bot sessions.
   - It finds its targets by content: every other `tests/` module that passes
     `--bare` or `--mirror`. `git clone --mirror` makes a bare repository too.
   - It runs each module in a child process whose HOME and XDG_CONFIG_HOME
     point at a scratch directory holding only a `.gitconfig` that sets
     `safe.bareRepository = explicit`, with every `GIT_*` variable dropped.
     HOME is the one channel that reaches the fixtures' git, because they drop
     `GIT_*` themselves.
   - The child imports the module the way `discover -s tests` does. It
     records `countTestCases()` before the run and `testsRun` and
     `wasSuccessful()` after, and the guard requires every defined test to
     run and pass. A class whose `setUpClass` dies shows up as `ran 0 of N`.
   - The child also asks git which `safe.bareRepository` it sees once the
     module is imported, and anything but `explicit` fails the module. A
     module, or a helper it imports, that gives git a config of its own on
     import would otherwise pass without the setting, and the guard with it.
     The shared isolation helper the family card plans is that shape, so its
     config has to carry the setting.
   - A second test feeds the harness three synthetic modules: the pre-fix
     shape, git run in `setUpClass` inside a bare repository found through
     the working directory; its `--git-dir=.` fix; and the pre-fix shape
     behind an import that moves HOME and sets `GIT_CONFIG_NOSYSTEM`. The
     first must come back `ran 0 of 1 tests, FAILED`, the second must pass,
     and the third, whose test passes, must be caught by the setting check.
     That proves the setting reaches git in the child, so the guard cannot
     pass on a config that stopped applying.
   - It skips outside a git checkout (sdist or wheel runs, where the
     claim-race module skips by design), without git, and with git older than
     2.38, which ignores the setting.
3. **Amended the two closed cards** with a post-close entry in each `log.md`
   naming the reproducer edit. Their verdicts are unchanged: each reproducer
   exits 0 under both configs.

Not the fix:

- `-c safe.bareRepository=all` on these calls, for the reason in step 1.
- Changing the workflows. The setting applies inside the session that runs
  the suite, `_env()` strips `GIT_*` overrides anyway, and AGENTS.md records
  that the bot cannot edit `.github/workflows/`.
