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

## 2026-11-16T04:42:04Z — Instance closed: the bare-repository hardening

[`regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories`](../regression-suite-is-red-in-bot-runs-whose-git-refuses-implicit-bare-repositories/)
closed. Its 11 reads inside a bare remote now pass `--git-dir`, so the
`bare-repos` config no longer changes the suite's result. `reproduce.py`,
re-run after that fix (git 2.56, Python 3.12):

```
control     ran 1501, OK
bare-repos  ran 1501, OK  [same as control]
signing     ran 1494, FAILED (errors=54)  [CHANGED]
              16 module(s) with errors or failures: ...
hooks       ran 1494, FAILED (errors=55)  [CHANGED]
              17 module(s) with errors or failures: ...

DEFECT: 2 of 3 host git config(s) change the suite's result (signing, hooks). The fixtures inherit the host's global git config.
```

It still exits 1. Signing and hooks still break 16 and 17 modules, with the
same error counts as filed. The suite gained 2 tests: the instance's guard,
which gives its children a HOME of its own and so passes under every config.

That guard puts one constraint on this card's fix, recorded in § Fix. It
fails any bare-remote module after whose import git no longer sees
`safe.bareRepository = explicit`. The shared helper sets HOME on import, so
its minimal `.gitconfig` has to carry that setting, or the guard turns red
on both modules. The summary, the Instances row and the bot-session bullet in
§ Why it matters now say the instance is fixed.
