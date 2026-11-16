## 2026-11-16T01:20:00Z — Filed by audit-deck after the pattern check

The audit filed
[regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories](../regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories/).
The Stop-hook pattern check then asked whether that instance belonged to a
broader pattern. Testing it meant running the full suite with HOME pointed at
a `.gitconfig` holding one other common setting at a time:

- `commit.gpgsign = true` with an unavailable key: 54 errors.
- A refusing global `core.hooksPath` pre-commit: 55 errors.
- A long `user.name`, `init.defaultBranch = trunk`, `pull.ff = only`,
  `core.autocrlf = true` and `user.useConfigOnly = true`: no change (1499
  tests, OK).

Two earlier sightings of the same family were never filed:

- A 2026-05 note on
  [test-move-asserts-old-inline-advances-format](../test-move-asserts-old-inline-advances-format/)
  about the host identity leaking into a board test. It promised a separate
  test-isolation card, but the follow-up fixed the board renderer instead.
- A 2026-05-18 closure that ran the suite under
  `GIT_CONFIG_GLOBAL=/dev/null` to get past it.

- **Dedup**: no card mentions `GIT_CONFIG_NOSYSTEM`, a hermetic or isolated
  git config for tests, `commit.gpgsign` or `core.hooksPath` as a test hazard.
  The only `GIT_CONFIG_GLOBAL` hits are the two workarounds above.
- **Edge**: the bare-repository card advances this one. That is the deck's
  meta-fix convention, an instance pointing at its umbrella. This card's DoD
  waits for every wired instance to close.
- **Gate `none`**: isolating test processes from the host's git config is
  standard practice. The open choice, a static or dynamic guard, is
  engineering, and the body recommends both shapes without needing a human
  pick.
