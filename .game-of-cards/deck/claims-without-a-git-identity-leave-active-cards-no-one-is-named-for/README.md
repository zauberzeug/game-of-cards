---
title: claims-without-a-git-identity-leave-active-cards-no-one-is-named-for
summary: "goc status <title> active took the claim identity only from --worker-who, an existing designation, or git config user.name. Containerised workers (CI images, agent sandboxes) often have no git identity, so the claim went through with no worker at all, leaving an active card no queue view can attribute unless every caller remembered the flag. Fixed: who and where now resolve from GOC_WORKER_WHO / GOC_WORKER_WHERE before git, and a claim no source can name is refused (exit 2, card unwritten)."
status: done
stage: null
contribution: medium
created: "2026-10-22T05:18:33Z"
closed_at: "2026-10-22T05:20:41Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `tests/test_claim_identity_from_env.py` pins the claim identity — an identity-less claim exits 2 naming both `--worker-who` and `GOC_WORKER_WHO` and leaves the card byte-identical; a blank variable counts as unset; `GOC_WORKER_WHO` / `GOC_WORKER_WHERE` supply the stamp; the flag beats the variable; an existing designation beats the variable; a line break in the variable is refused without a traceback
  - [x] MECHANICAL: every existing test that claimed in a temp dir without a repo-local git identity names one (`--worker-who`), and the tests that assert a git-derived or absent identity scrub `GOC_WORKER_WHO` / `GOC_WORKER_WHERE`, so CI (no git identity configured) and a shell that sets the variables both stay green
  - [x] MECHANICAL: AGENTS.md's `worker` bullet, `card-schema` and `advance-card` (core and `reference.md` § Worker field) document the resolution order and keep the variables apart from the `GOC_WORKER` queue filter; plugin mirrors synced and the OpenClaw skills re-ported
  - [x] PROCESS: `uv run goc validate` passes
worker: {who: Rodja Trappe, where: feat/claim-identity-from-env}
---

# Claims without a git identity leave active cards no one is named for

## Location

- `goc/engine.py` — `_auto_populate_worker` resolved `who` from
  `--worker-who`, else the card's existing designation, else
  `git config user.name`, and `where` from `--worker-where`, else the
  current branch.
- `goc/engine.py` — `_cmd_status`, the `new_status == "active"` branch:
  when no `who` resolved, `_auto_populate_worker` returned the card text
  unchanged and the claim was written anyway.

## What was broken

A claim is supposed to say who works the card; `worker` is what
`goc --worker <X>`, the active-card notice and the claim-race checks
read. Containerised workers routinely have no git identity at all — no
repo-local config, no `~/.gitconfig`, no `/etc/gitconfig` — and GitHub
runners set none either. In such an environment
`goc status <title> active` succeeded and left `status: active` with no
`worker` line, unless the caller remembered `--worker-who` on every
claim. The June fix in
[goc-status-active-stamps-empty-who-worker-when-git-user-name-unset](../goc-status-active-stamps-empty-who-worker-when-git-user-name-unset/)
deliberately stopped stamping the invalid `{who: "", where: <branch>}`
mapping and let the transition succeed without a stamp; that removed the
corrupt frontmatter but kept the unattributed claim.

## Evidence

The identity-less case is pinned in `tests/test_claim_identity_from_env.py`,
which binds every identity source explicitly (`GIT_CONFIG_GLOBAL` and
`GIT_CONFIG_SYSTEM` set to `os.devnull`, `GOC_WORKER_*` scrubbed) so it
cannot pass by inheriting a developer's git config. Before the fix that
claim exited 0 and wrote `status: active` with no `worker`; after it the
claim exits 2 with

```
ERROR: claim-probe: cannot claim without a worker identity — the card has no worker, GOC_WORKER_WHO is unset and git user.name is unavailable. Pass --worker-who <identity> or set GOC_WORKER_WHO.
```

and the card is byte-identical.

## Fix

- `who` resolves from `--worker-who`, else the existing designation, else
  `GOC_WORKER_WHO`, else `git config user.name`; `where` from
  `--worker-where`, else `GOC_WORKER_WHERE`, else the current branch (a
  detached HEAD still keeps a stored `where`). A blank variable counts as
  unset. The variables make the identity a property of the execution
  context, which is where a container's identity actually lives.
- `_cmd_status` refuses a claim no source can name, after
  `_auto_populate_worker` and before the write, so the refusal leaves the
  card untouched.
- The variables get the same boundary check as the flags
  (`_reject_invalid_worker_flag`): a line break inside `GOC_WORKER_WHO`
  would otherwise reach the emitter as a `FrontmatterError` traceback.
- `GOC_WORKER` stays what it was — a queue filter. The docs now say so
  next to the new variables, because the names are close.

## Scope

The identity change comes from PR #11, which also proposed three
lifecycle changes that no card had decided: `goc validate` requiring
`worker` on every active card, clearing `worker` when a card is
re-queued, and `goc wait` releasing an active claim (with
`--keep-claim`). Clearing `worker` on release deletes pre-assignments
such as `worker: gpu-required` (measured), so those changes went to the
decision card
[parked-claims-stay-active-under-goc-wait-and-release-has-no-rule-for-the-worker](../parked-claims-stay-active-under-goc-wait-and-release-has-no-rule-for-the-worker/)
instead of landing here.

This does **not** fix
[worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/):
that defect is `_emit_worker` re-emitting a hand-authored
`worker: {where: x}` through `goc wait` / `decide` / `advance`, a path the
claim never takes. Its `reproduce.py` still reports the defect with this
change applied.
