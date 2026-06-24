---
title: closure-on-integration-check-conflates-git-error-with-not-integrated
status: done
stage: null
contribution: low
created: "2026-06-24T01:27:36Z"
closed_at: "2026-06-24T01:31:22Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug]
summary: |
  _enforce_closure_on_integration_or_exit treats every non-zero `git
  merge-base --is-ancestor` exit as "HEAD is not reachable", collapsing
  exit 1 (genuinely not integrated — the intended block) with exit 128
  (git error, e.g. origin/main not resolvable). On a git error it fails
  closed with a misleading message instead of warn-and-skipping like the
  sibling fetch-failure branch directly above it.
definition_of_done: |
  - [x] TDD: reproduce.py exits zero (defect no longer fires) — a 128-class
        git error from merge-base no longer blocks closure with the
        "HEAD is not reachable" message
  - [x] TDD: a true non-ancestor (exit 1) still blocks closure with the
        "not reachable from origin/main" error and `sys.exit(2)`
  - [x] MECHANICAL: the merge-base branch distinguishes exit 1 (block)
        from other non-zero exits (warn-and-skip), mirroring the
        fetch-failure branch above it
worker: {who: "claude[bot]", where: main}
---

# closure-on-integration-check-conflates-git-error-with-not-integrated

## Location

`goc/engine.py:4184-4197`, in `_enforce_closure_on_integration_or_exit`.

## What's broken

When `workflow.closure_on_integration` is enabled, closure is gated on
HEAD being reachable from `origin/main`. The check runs `git merge-base
--is-ancestor` and tests the exit code:

```python
check = subprocess.run(
    ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
    capture_output=True,
    cwd=git_cwd,
    check=False,
)
if check.returncode != 0:
    print(
        f"ERROR: {title}: closure_on_integration is enabled and HEAD is not"
        " reachable from origin/main. Integrate the work (merge or push)"
        " before closing — `done` must be visible to every participant.",
        file=sys.stderr,
    )
    sys.exit(2)
```

`git merge-base --is-ancestor` defines **three** exit codes:

- `0` — HEAD *is* an ancestor (integrated) → allow closure.
- `1` — HEAD is *not* an ancestor (genuinely not integrated) → the
  intended block.
- `128` — a git **error** (e.g. `origin/main` is not a resolvable ref,
  HEAD is unborn, the object is missing).

The `!= 0` test collapses `1` and `128` into the same block. On a git
error the card is refused closure with the message *"HEAD is not
reachable from origin/main"* — a misdiagnosis (the true cause is a ref
error, not un-integrated work) and the wrong policy: it fails **closed**.

The sibling branch immediately above — the `git fetch` guard at
`engine.py:4178` — chose the opposite, correct posture for a git failure:

```python
if fetch.returncode != 0:
    print(
        "  Warning: closure_on_integration is enabled but `git fetch origin main` failed; skipping check",
        file=sys.stderr,
    )
    return
```

It **warns and skips** (fails open) when git can't answer. The merge-base
branch should follow the same convention for its own git-error case (exit
128), reserving the hard `sys.exit(2)` block for exit `1`.

## Empirical evidence

`reproduce.py` stubs the merge-base subprocess to return each exit code.
After the fix:

```
merge-base exit 0   (integrated)      -> ('ok', None)
merge-base exit 1   (not an ancestor) -> ('exit', 2)
merge-base exit 128 (git error)       -> ('ok', None)

exit 0   allows closure:        PASS
exit 1   blocks closure (2):    PASS
exit 128 warns & skips:         PASS

PASS: git error is no longer conflated with not-integrated.
```

Before the fix, `exit 128` returned `('exit', 2)` (FAIL) — a git error was
treated as un-integrated work.

## Why it matters

Reachability path: a consumer enables `closure_on_integration: true` in
`.game-of-cards/config.yaml`, then runs `goc done <card>`. The
`git fetch origin main` succeeds (exit 0) but `refs/remotes/origin/main`
is not populated — realistic when the origin remote's fetch refspec is
not the standard `+refs/heads/*:refs/remotes/origin/*` (e.g. a remote
added with `--no-tags`/explicit single-ref refspec, some CI checkouts, or
a shallow/worktree clone configured to fetch into `FETCH_HEAD` only).
`git merge-base --is-ancestor HEAD origin/main` then exits 128 because
`origin/main` doesn't resolve, and the engine blocks the close with a
message blaming un-integrated work. The user is told to "merge or push"
work that is in fact already integrated; the real fix is a remote-config
issue the message never names.

Distinct from
[closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded](../closure-on-integration-check-only-runs-for-done-not-disproved-or-superseded/),
which concerns *which verbs* invoke the check (scope), not the exit-code
handling inside it.

## Fix (applied)

The merge-base branch now distinguishes exit `1` (block) from any other
non-zero exit (warn and skip), mirroring the fetch-failure branch. Covered
by `tests/test_closure_on_integration_git_error.py` (exit 0 allows, exit 1
blocks with `sys.exit(2)`, exit 128 warns and skips):

```python
check = subprocess.run(
    ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
    capture_output=True,
    cwd=git_cwd,
    check=False,
)
if check.returncode == 1:
    print(
        f"ERROR: {title}: closure_on_integration is enabled and HEAD is not"
        " reachable from origin/main. Integrate the work (merge or push)"
        " before closing — `done` must be visible to every participant.",
        file=sys.stderr,
    )
    sys.exit(2)
if check.returncode != 0:
    print(
        "  Warning: closure_on_integration is enabled but `git merge-base"
        " --is-ancestor` could not determine reachability (git error);"
        " skipping check",
        file=sys.stderr,
    )
    return
```
