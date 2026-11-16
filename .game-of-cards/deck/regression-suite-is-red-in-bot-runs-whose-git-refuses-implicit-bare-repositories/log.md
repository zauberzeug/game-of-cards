## 2026-11-16T00:58:33Z — Filed by audit-deck

Found by the audit's probe rather than by static hunting. The regression
suite, run inside this audit-deck session, reported `Ran 1492 tests` and
`FAILED (errors=2)`. Both errors are `setUpClass` failures on
`git rev-parse main` run inside a bare remote. The cause is `~/.gitconfig`,
which held `[safe] bareRepository = explicit`. It was written at session
start by `prepareGitForSession` in `anthropics/claude-code-action@v1`, and the
action's `docs/security.md` documents it. With HOME pointed at an empty
`.gitconfig` the same tree runs 1499 tests, OK. A scratch clone with
`--git-dir=.` added at the 11 bare-remote call sites also runs 1499 tests, OK,
under the hardened config.

- **Dedup**: no card mentions `bareRepository`, `safe.bare`, `bare repository`
  or `bare repo`, and none covers tests that depend on the host's git config.
  Two cards come closest.
  [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/)
  is about a different failing test.
  [autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing](../autonomous-pushes-do-not-trigger-ci-so-the-regression-suite-gates-nothing/)
  explains why a bot's own run is the only gate on its commits.
- **Sibling sweep**:
  - `tests/`: the only 2 modules that create a bare repository are both
    affected.
  - Deck reproducers: 2 of the 5 that use a bare remote are affected, both on
    closed cards. Each closed card got a post-close amendment pointing here.
    The 3 on open cards print the same exit code and verdict under both
    configs.
  - `goc/`, `scripts/`, `.github/`: none runs git inside a bare repository.
- **Gate `none`**: there is one mechanical fix path, `--git-dir`, and the
  action's own docs prescribe it.
- **Contribution `high`**: 55 live cards' DoD requires the suite to pass, and
  the suite is the only gate on bot commits.

## 2026-11-16T04:26:41Z — Claimed; the new guard is red on today's fixtures

Claimed by pull-card. This session's `~/.gitconfig` again holds only
`[safe] bareRepository = explicit`, and `reproduce.py` exits 1 with 4 of 4
targets diverging, as filed.

Wrote the guard first: `tests/test_bare_repository_fixtures_name_their_git_dir.py`.
It runs every other `tests/` module that passes `--bare` or `--mirror` in a
child process whose HOME holds only a `.gitconfig` setting
`safe.bareRepository = explicit`, and requires each module to run every test
it defines (`countTestCases()`, counted in the child) and pass. A second test
feeds the harness two synthetic modules, the pre-fix shape (git run inside a
bare repository found through the working directory, in `setUpClass`) and the
fixed one (`--git-dir=.`). It requires `ran 0 of 1 tests, FAILED` for the
first and a pass for the second. That proves the hardened HOME reaches git in
the child, so the guard cannot pass on a config that stopped applying.

Run against the unfixed fixtures at `a3d452b9`:

```
FAIL: test_every_bare_repository_module_runs_all_its_tests_and_passes
  tests/test_claim_race_reassurance.py: ran 0 of 4 tests, FAILED
      subprocess.CalledProcessError: Command '['git', 'rev-parse', 'main']' returned non-zero exit status 128.
  tests/test_deck_location_claim_rows.py: ran 0 of 3 tests, FAILED
      subprocess.CalledProcessError: Command '['git', 'rev-parse', 'main']' returned non-zero exit status 128.
Ran 2 tests
FAILED (failures=1)
```

The harness self-test passed in the same run.

## 2026-11-16T04:42:16Z — Closure

- **What changed**: `tests/test_claim_race_reassurance.py` and
  `tests/test_deck_location_claim_rows.py` got a `_remote_git(remote, *args)`
  helper that passes `--git-dir=<remote>`, and their 2 and 3 reads inside the
  bare remote use it. The reproducer of
  `deck-location-doc-says-claims-push-by-default-and-last-writer-wins` got the
  same helper for its 5 reads. The reproducer of
  `deck-skill-promises-git-merge-settles-claim-races-the-default-config-never-detects`
  passes the flag at its 1 read. Each of the two closed cards has a post-close
  amendment in its `log.md`. New guard:
  `tests/test_bare_repository_fixtures_name_their_git_dir.py`, 2 tests. It runs
  every other `tests/` module that passes `--bare` or `--mirror` in a child
  under a HOME whose `.gitconfig` sets only `safe.bareRepository = explicit`.
  Each module must run all its `countTestCases()` tests and pass, and git must
  still see `explicit` once the module is imported. A self-test feeds the
  harness three synthetic modules. Nothing passes
  `-c safe.bareRepository=all`.
- **Added after the red run**: the setting check. The family card's planned
  fix gives git a config of its own on import, which would have let both
  bare-remote modules pass without the setting, and the guard with them. The
  third synthetic module, the pre-fix shape behind an import that moves HOME,
  proves the check fires. Its prelude also sets `GIT_CONFIG_NOSYSTEM`, so a
  host whose system config already hardens git still gets the expected
  verdicts. That was checked by passing a hardened
  `GIT_CONFIG_SYSTEM` through to the children. Re-run in a temporary worktree
  at `a3d452b9`, the updated guard fails the unfixed fixtures the same way:
  `ran 0 of 4 tests, FAILED` and `ran 0 of 3 tests, FAILED`.
- **Verification**: `reproduce.py` exits 0, with all 5 targets the same under
  both configs (its scan now also finds the guard). Full suite, Python 3.12:
  `Ran 1501 tests`, `OK` under this session's `~/.gitconfig` (only
  `safe.barerepository=explicit`), and `Ran 1501 tests`, `OK` with HOME and
  XDG_CONFIG_HOME on a scratch dir whose `.gitconfig` is empty. The 2 tests
  above the filing count of 1499 are the guard's. The guard and both fixed
  modules also pass under pytest and under Python 3.14.
- **Family card**: `test-fixtures-run-git-under-the-hosts-global-config-and-break-on-common-settings`
  stays open. Its reproducer, re-run after the fix, shows `bare-repos`
  matching the control (`ran 1501, OK`), while signing (54 errors) and hooks
  (55 errors) still break the suite. Its summary, Instances row and
  bot-session bullet now record this instance as fixed. Its § Fix names
  the setting its isolation helper's config must carry. Its `log.md` has
  the run.
- **Audit**: no rubric configured; mechanical fix
- **Project impact**: n/a
- **Tests**: 1501 passed / 0 failed / 0 xfailed
  (`uv run python -m unittest discover -s tests`, under both git configs).
  `uv run goc validate`, `scripts/sync_plugin_assets.py --check`,
  `scripts/check_card_language.py` and
  `scripts/check_card_frontmatter_yaml.py` all exit 0.

## Closure verification (2026-11-16T04:42:33Z)

### Layer-3 (GoC DoD)

- [x] advanced-by-closed — no advanced_by edges
- [x] dod-100-percent — 4/4 ticked
- [x] log-md-closure-entry — '## 2026-11-16T04:42:16Z — Closure' present
