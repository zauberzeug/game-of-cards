---
title: goc-status-active-drops-prior-worker-where-on-detached-head-reclaim
summary: "When `goc status <t> active` re-claims a card on a detached HEAD (or any state where `git rev-parse --abbrev-ref HEAD` fails or returns `HEAD`), `_auto_populate_worker` silently emits the worker field as a bare string and drops the prior `where`. The `who` sub-field has a fallback to `existing_dict['who']`; the `where` sub-field has no symmetrical fallback — live branch detection failing collapses the mapping to bare-string, destroying the prior branch record."
status: open
stage: null
contribution: medium
created: "2026-05-31T01:53:34Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (fall back to `existing_dict['where']` when branch detection yields nothing, OR refuse the transition with a clear error, OR keep current behavior and document the silent drop as intentional).
  - [ ] TDD: reproduce.py exits zero (the chosen behavior is observed).
  - [ ] TDD: a unit test in `tests/` covers the `worker_where is None AND existing_dict has where AND git rev-parse returns 'HEAD'` path.
  - [ ] MECHANICAL: `_auto_populate_worker` docstring at `goc/engine.py:4148` updated to match the chosen behavior.
  - [ ] PROCESS: `uv run goc validate` passes.
---

# `goc status active` drops prior `worker.where` on detached-HEAD reclaim

## Location

`goc/engine.py:4172-4189` — `_auto_populate_worker`.

## What's broken

`_auto_populate_worker` populates the `worker` field with an
**asymmetric fallback policy** for the two sub-fields. The `who`
branch falls back to the existing frontmatter when no explicit
override is given:

```python
4164:    if worker_who is not None:
4165:        who = worker_who
4166:    elif "who" in existing_dict:
4167:        who = existing_dict["who"]      # ← fallback to prior who
4168:    else:
4169:        r = subprocess.run(["git", "config", "user.name"], ...)
4170:        who = r.stdout.strip() if r.returncode == 0 else ""
```

The `where` branch has **no symmetrical fallback**. It jumps
straight from "no override" to "live detection" and treats failure
as absent:

```python
4172:    if worker_where is not None:
4173:        where: str | None = worker_where
4174:    else:
4175:        r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)
4176:        where = r.stdout.strip() if r.returncode == 0 else None
4177:        if where in ("", "HEAD"):
4178:            where = None
```

When `where` ends up `None`, the emitter collapses the worker
mapping back to a bare string:

```python
4185:    if where:
4186:        where_yaml = _yaml_inline(where)
4187:        worker_yaml = f"{{who: {who_yaml}, where: {where_yaml}}}"
4188:    else:
4189:        worker_yaml = who_yaml      # ← bare string; prior where is gone
```

So a card filed with `worker: {who: alice, where: feature/x}`,
released to `status: open`, and then re-claimed via `goc status …
active` from a detached HEAD checkout is rewritten as bare-string
`worker: alice` — the `where: feature/x` record is silently
destroyed.

The function's own docstring at `goc/engine.py:4149-4154` codifies
the intent:

> If the card already has a worker.who (designation), preserve it
> and only add/update `where`. […] Explicit --worker-who /
> --worker-where flags override auto-detection for either
> sub-field.

The docstring says "add/update `where`," but the implementation
also *deletes* it when live detection fails — without that being
mentioned anywhere.

## Reachability path

Triggered from `_cmd_status` at `goc/engine.py:4193` on every
`open/blocked → active` transition. Concrete flows that reach a
detached HEAD or no-branch state:

- `git checkout <sha>` for a code-archaeology / bisect session,
  followed by a deliberate `goc status … active` on a card
  the agent decides to claim from that checkout.
- CI workflows that check out an explicit ref (e.g. tag) and then
  exercise `goc status` against the deck — `actions/checkout` with
  `ref:` set to a tag or SHA leaves the runner on a detached HEAD.
- `git worktree add --detach <path>` worktrees, used by
  multi-agent setups (per `support-worktrees-and-multi-agent-deck-sync`
  in the closed deck).
- Any local custom workflow where the user checks out by SHA
  before re-claiming.

The `worker` field is the audit record of *who and where* is
responsible right now. The `where` sub-field encodes branch
context that filters and the board's display use to disambiguate
parallel agents. Silently dropping it on re-claim is the same
class of record-corruption as the sibling card
`goc-status-active-preserves-prior-worker-who-on-reclaim`
(asymmetric refresh of the OTHER direction), and the resolution
likely belongs in the same design pass.

## Empirical evidence

`uv run python .game-of-cards/deck/goc-status-active-drops-prior-worker-where-on-detached-head-reclaim/reproduce.py`:

```
abbrev-ref HEAD before claim: 'HEAD'
worker field after detached-HEAD reclaim: worker: alice
RESULT: prior `where: feature/x` was silently dropped — defect FIRED.
```

Exit code 2. The reproducer scaffolds a card carrying
`worker: {who: alice, where: feature/x}`, detaches HEAD, and runs
`goc status demo-card active`. The worker field is rewritten to
the bare string `worker: alice`; the `where: feature/x` record is
gone with no warning.

## Why it matters

This is the 6th distinct defect filed against `_auto_populate_worker`
and the worker emitter (alongside
[goc-status-active-preserves-prior-worker-who-on-reclaim](../goc-status-active-preserves-prior-worker-who-on-reclaim/),
[goc-status-active-discards-worker-overrides-when-target-already-active](../goc-status-active-discards-worker-overrides-when-target-already-active/),
[goc-status-silently-drops-worker-overrides-on-non-active-transitions](../goc-status-silently-drops-worker-overrides-on-non-active-transitions/),
[emit-frontmatter-silently-strips-unknown-worker-sub-keys](../emit-frontmatter-silently-strips-unknown-worker-sub-keys/),
and [worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/)).
The recurring shape is "sub-fields are populated by independent
policies that don't agree on what a missing input means." A worker
meta-fix consolidating these may be the better next step than
patching each instance — but this card documents the specific
detached-HEAD failure so it isn't lost to the family.

## Decision required

Three credible resolutions:

1. **Add the symmetrical fallback.** When `worker_where is None`
   and `where` resolves to `None` from the live check, fall back
   to `existing_dict.get("where")`. Mirrors the `who` policy at
   line 4166-4167. Pro: closest to the docstring's stated intent
   ("add/update `where`"). Con: a worker that actually moved to a
   detached-HEAD checkout will see a stale branch label.
2. **Refuse the transition with a clear error.** If live branch
   detection fails AND the card has a prior `where`, emit
   `ERROR: branch detection failed; pass --worker-where to refresh
   the where sub-field` and exit non-zero. Pro: never silently
   destroys information. Con: blocks autonomous flows from
   detached-HEAD checkouts.
3. **Document current behavior as intentional.** Update the
   docstring to "where is refreshed from the live branch on every
   re-claim, and dropped if the live branch is unavailable" and
   close. Pro: zero code change. Con: contradicts the user-visible
   contract; cold readers won't expect a silent drop.

Cross-cutting note: the sibling card
[goc-status-active-preserves-prior-worker-who-on-reclaim](../goc-status-active-preserves-prior-worker-who-on-reclaim/)
is parked at the same gate and is the inverse asymmetry (who
preserved, where always refreshed). A unified decision covering
both — "refresh both" / "preserve both as a unit" / "preserve both
with explicit-override refresh" — would resolve this card too. The
resolution should be coordinated with that card.

## Fix

If option 1 is chosen:

```python
# goc/engine.py:4172-4178
if worker_where is not None:
    where: str | None = worker_where
else:
    r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], ...)
    where = r.stdout.strip() if r.returncode == 0 else None
    if where in ("", "HEAD"):
        where = None
    if where is None and "where" in existing_dict:
        where = existing_dict["where"]
```

If option 2 is chosen: insert an explicit check after live
detection that fails the command with the suggested error message
when the prior `where` exists and no override was supplied.
