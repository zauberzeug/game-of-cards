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
