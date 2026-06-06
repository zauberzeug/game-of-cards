---
title: goc-status-active-stamps-empty-who-worker-when-git-user-name-unset
summary: "`goc status <card> active` self-corrupts: when git `user.name` is unset but the tree is on a named branch, `_auto_populate_worker` writes `worker: {who: \"\", where: <branch>}` — a mapping `goc validate` rejects (`'who' must be a non-empty string`). The claim succeeds but immediately fails validation. Fix: skip stamping a worker when `who` is empty (a `where`-only worker is itself invalid)."
status: open
stage: null
contribution: medium
created: "2026-06-06T04:50:09Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: reproduce.py exits 1 after the fix (no empty-`who` worker is stamped) — exits 0 on the unfixed engine
  - [ ] TDD: a unit test in tests/ asserts `_auto_populate_worker` returns the card text UNCHANGED when `who` resolves empty and only a branch is known
  - [ ] MECHANICAL: `uv run goc validate` clean; plugin mirrors synced (`python scripts/sync_plugin_assets.py --check`)
  - [ ] PROCESS: closure entry in log.md records the chosen fix and why skipping (not where-only stamping) is forced
---

# `goc status active` stamps an invalid empty-`who` worker when git user.name is unset

## Location

`goc/engine.py:4290-4300` — `_auto_populate_worker`.

## What's broken

`_auto_populate_worker` resolves `who` from (in order) the `--worker-who`
flag, an existing `worker.who`, or `git config user.name`; and `where` from
`--worker-where` or the current branch. On a checkout where git `user.name`
is not configured, the git lookup returns empty:

```python
        r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        who = r.stdout.strip() if r.returncode == 0 else ""
```

The only no-op guard fires when BOTH are empty:

```python
    if not who and not where:
        return text

    # Build the YAML inline value and mutate the frontmatter line-anchored.
    who_yaml = _yaml_inline(who) if who else '""'
    if where:
        where_yaml = _yaml_inline(where)
        worker_yaml = f"{{who: {who_yaml}, where: {where_yaml}}}"
    else:
        worker_yaml = who_yaml
    return mutate_frontmatter_field(text, "worker", worker_yaml)
```

So when `who` is empty but `where` is a real branch, the guard is skipped,
`who_yaml` becomes the literal `""`, and the function hand-builds
`worker: {who: "", where: <branch>}`. That value round-trips to
`{'who': '', 'where': '<branch>'}`, which `validate_card` rejects at
`goc/engine.py:1391-1392`:

```python
            elif not isinstance(worker.get("who"), str) or not worker["who"].strip():
                errors.append(f"{t.title}: worker: 'who' must be a non-empty, non-whitespace string")
```

The status flip succeeds and the file is written, but the card now fails
`goc validate` — a silent self-corruption produced by a routine claim.

## Empirical evidence

`uv run python deck/goc-status-active-stamps-empty-who-worker-when-git-user-name-unset/reproduce.py`:

```
git user.name = ''; branch = 'main'
emitted worker line: 'worker: {who: "", where: main}'
re-parsed worker  : {'who': '', 'where': 'main'}
validate_card worker errors: ["demo-card: worker: 'who' must be a non-empty, non-whitespace string"]
DEFECT REPRODUCED: claim stamped an invalid empty-`who` worker that fails goc validate.
```

## Why it matters

The reachability path is a stock CI / container checkout: GitHub Actions and
many container images do not set a global `git config user.name` (identity is
passed per-commit via `-c user.name=...` or `GIT_AUTHOR_NAME`), yet the tree
is on a named branch. An autonomous `pull-card` / `goc status active` claim in
that environment writes a card that then trips the very `goc validate` gate CI
runs in `.github/workflows/ci.yml`, turning a normal claim into a red build.

This is a **distinct code site** from
[worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/),
which is about `_emit_worker` (`engine.py:270`) *re-emitting* an already-stored
`{where: x}` dict and is parked UNVERIFIED because its reachability was unclear.
Here the bad value is constructed inline by `_auto_populate_worker` on the
*first* claim — it never passes through `_emit_worker` — and the reachability
is proven above. The two cards share the "empty-`who` worker is invalid" root
shape but fire from different sites; this one carries the proof and a
decision-free fix.

## Fix

Extend the no-op guard so the function never stamps a worker it cannot make
valid. A `where`-only worker is itself rejected by the schema (`where`
requires `who`), so when `who` is empty there is no valid worker to write —
skip it, exactly as the both-empty case already does:

```python
    if not who:
        return text
```

placed where the current `if not who and not where:` guard sits (the
`not where` branch is then subsumed). The status transition still succeeds; it
simply records no worker stamp when identity is unknown — the same outcome a
fully-unconfigured checkout already gets today. This is forced, not a taste
call: the only alternatives (`{who: "", where: ...}` or `{where: ...}`) are
both invalid frontmatter.
