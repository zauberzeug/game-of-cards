---
title: closure-on-integration-check-silently-skips-on-non-origin-main-repos
summary: "workflow.closure_on_integration hardcodes 'git fetch origin main' and 'origin/main' in _enforce_closure_on_integration_or_exit; on any repo whose canonical branch is master/trunk/develop or whose remote is not named origin, the fetch always fails and the guard warns-and-skips, so the opt-in integration policy is a permanent silent no-op and unintegrated work closes as done with exit 0."
status: open
stage: null
contribution: high
created: "2026-07-24T01:57:21Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero (a master-branch repo with unpushed HEAD is blocked from `goc done`, or fails loudly instead of warn-and-skip)
  - [ ] TDD: regression test covers the chosen canonical-branch resolution (non-main branch enforced; unresolvable canonical ref does not close silently)
  - [ ] MECHANICAL: the decision below is recorded and the fix lands in _enforce_closure_on_integration_or_exit with the docstring updated
  - [ ] MECHANICAL: uv run goc validate passes
  - [ ] PROCESS: decision recorded via goc decide (which canonical-ref resolution wins)
---

# closure-on-integration-check-silently-skips-on-non-origin-main-repos

## Summary

`workflow.closure_on_integration` hardcodes `git fetch origin main` and
`origin/main` in `_enforce_closure_on_integration_or_exit`; on any repo whose
canonical branch is `master`/`trunk`/`develop` — or whose remote is not named
`origin` — the fetch always fails and the guard warns-and-skips, so the opt-in
integration policy is a permanent silent no-op and unintegrated work closes as
`done` with exit 0.

## Location

`goc/engine.py:4557-4606` (`_enforce_closure_on_integration_or_exit`), the
hardcoded names at lines 4573 and 4586.

## What's broken

The docstring promises a policy:

> Multi-team policy: a card cannot transition to `done` until its work is
> integrated to the canonical branch — `done` must mean "visible to every
> participant", not just "locally DoD-complete". Opt-in; default off.

The implementation pins "the canonical branch" to two literal names:

```python
fetch = subprocess.run(
    ["git", "fetch", "--quiet", "origin", "main"],   # engine.py:4573
    ...
)
if fetch.returncode != 0:
    print(
        "  Warning: closure_on_integration is enabled but `git fetch origin main` failed; skipping check",
        file=sys.stderr,
    )
    return
check = subprocess.run(
    ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],  # engine.py:4586
    ...
)
```

On a repo whose default branch is `master` (still the git-init default without
`init.defaultBranch` configured), or `trunk`/`develop`, or whose remote is not
named `origin`, `git fetch origin main` fails **every time**. The fetch-failure
branch — added by the closed card
[closure-on-integration-check-conflates-git-error-with-not-integrated](../closure-on-integration-check-conflates-git-error-with-not-integrated/)
to stop transient git errors from *blocking* closes — then downgrades the
permanent misconfiguration to a stderr warning and returns. The user opted in
to "refuse closure unless integrated" and gets "always close, warn to a stream
most agent harnesses swallow".

## Empirical evidence

`uv run python .game-of-cards/deck/closure-on-integration-check-silently-skips-on-non-origin-main-repos/reproduce.py`:

```
[1] canonical branch `main`, unpushed HEAD -> `goc done` exit 2 (policy blocks the close): True
[2] canonical branch `master`, unpushed HEAD -> `goc done` exit 0; stderr says 'skipping check': True
[FAIL] the opt-in integration policy silently no-ops on a master-branch repo: identical unintegrated work closes as done
```

Identical unintegrated state; only the branch name differs.

## Why it matters

This is an explicitly opted-in safety policy that never fires on a large class
of real repos, and its failure mode is invisible (one stderr warning per
close). Reachability: any consumer repo with `workflow.closure_on_integration:
true` whose default branch predates the `main` rename — no exotic input
required. The deck already treats hardcoded `origin/main` as a defect shape
elsewhere:
[standup-underreports-closures-and-ignores-unpulled-remote-commits](../standup-underreports-closures-and-ignores-unpulled-remote-commits/)
praises `@{u}` precisely because it avoids hardcoding `origin/main`.

## Decision required

How should the guard resolve "the canonical branch"? Credible options:

1. **`origin/HEAD` symbolic ref** — `git symbolic-ref refs/remotes/origin/HEAD`
   (populated by clone; repairable via `git remote set-head origin -a`). Closest
   to "the remote's default branch", but may be unset in repos created by
   `git init` + `git remote add`, so it needs a fallback or a loud error.
2. **Upstream tracking ref `@{u}`** — matches the precedent the standup fix
   set. But "my branch's upstream" is not "the canonical branch": on a feature
   branch with its own upstream, pushing the feature branch would satisfy the
   check without integration to main.
3. **Config key** — `workflow.integration_branch` (e.g. `origin/main` default)
   so multi-team repos can pin `trunk`/`develop` explicitly; combine with (1)
   as the default when the key is absent.
4. **Any of the above + loud failure**: when the canonical ref cannot be
   resolved, exit 2 with a config hint instead of warn-and-skip — a permanent
   misconfiguration of an opted-in policy should not be silent. (This
   sub-decision applies whichever resolution wins.)

Option 3+1 (config key defaulting to detected `origin/HEAD`, loud failure when
unresolvable) covers every observed shape; option 2 alone is unsound for the
policy's stated goal.
