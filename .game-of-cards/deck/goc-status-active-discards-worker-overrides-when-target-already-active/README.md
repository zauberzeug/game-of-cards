---
title: goc-status-active-discards-worker-overrides-when-target-already-active
summary: "`goc status <t> active --worker-who alice --worker-where feature/foo` silently does nothing when `<t>` is already in `status: active`. `_cmd_status` early-returns at `engine.py:3972-3981` whenever `prior == new_status`, BEFORE the `_auto_populate_worker` path that honors the override flags. The argparser at `engine.py:2619-2622` advertises both flags with no restriction on when they take effect, so a CI runner or replacement claimant invoking the verb to update worker metadata sees zero error and zero state change — the flags are dropped on the floor."
status: open
stage: null
contribution: medium
created: "2026-05-29T19:17:12Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - goc-status-active-preserves-prior-worker-who-on-reclaim
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (honor the override flags on no-op reclaim, OR keep silent-drop and document it in `--worker-who` / `--worker-where` help text, OR exit with a non-zero "card already active; release first" diagnostic when overrides are passed).
  - [ ] TDD: `reproduce.py` exits zero — the chosen behavior matches expectation across the matrix (active card with no overrides; active card with `--worker-who` only; active card with `--worker-where` only; active card with both).
  - [ ] TDD: a unittest under `tests/` exercises `goc status <t> active --worker-who <new>` on an already-active card and asserts the chosen behavior so a future `_cmd_status` refactor cannot reintroduce the silent drop.
  - [ ] MECHANICAL: argparser help text at `engine.py:2619-2622` (`--worker-who`, `--worker-where`) reads consistently with the chosen behavior.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# `goc status active` discards worker overrides when the target is already active

## Location

- Early-return path: `goc/engine.py:3972-3981`
- Worker-update path that is bypassed: `goc/engine.py:4001-4002` (`_auto_populate_worker`)
- Argparser that advertises the dropped flags: `goc/engine.py:2619-2622`

## What's broken

`_cmd_status` checks for a no-op transition first:

```python
3972:    if prior == new_status:
3973:        if new_status == "active":
3974:            print(
3975:                f"WARNING: {title}: already active — possible racing claim;"
3976:                f" check `goc --status active` before proceeding",
3977:                file=sys.stderr,
3978:            )
3979:        else:
3980:            print(f"{title}: already {new_status}; nothing to do")
3981:        return
```

When `prior == new_status == "active"`, the function prints the
racing-claim WARNING to stderr and `return`s — without ever
consulting `args.worker_who` or `args.worker_where`. The override
flags are silently dropped on the floor.

The argparser claims the flags work on every `goc status` flip:

```python
2619:    p_status.add_argument("--worker-who", default=None,
2620:                          help="Override worker.who identity.")
2621:    p_status.add_argument("--worker-where", default=None,
2622:                          help="Override worker.where branch or path for this claim.")
```

No restriction; no help-text caveat. A user reading `goc status --help`
sees flags that accept any value, with no hint that the value is
discarded when the target is already in the requested status.

## Empirical evidence

Reproducer output (from `reproduce.py`):

```
=== After 1st claim ===
worker: alice-orig
=== 2nd 'goc status active' with bob overrides ===
WARNING: sample-card: already active — possible racing claim; check `goc --status active` before proceeding
=== After 2nd attempt (worker should be bob if flags honored) ===
worker: alice-orig
```

The second invocation passed `--worker-who bob --worker-where
feature/bar`. Exit code was 0; the WARNING went to stderr; the worker
field on disk remained `alice-orig`.

## Why it matters

Reachability path: any agent or CI runner that tries to update worker
metadata on an already-active card hits this. Concrete flow:

1. Runner A claims card X via `goc status X active` — `worker:
   runner-a`.
2. Runner A's session crashes; the card stays `active` (no
   `goc status X open` release).
3. Runner B picks the card up and runs `goc status X active
   --worker-who runner-b --worker-where ci-job-1234` intending to
   record its identity for the operator dashboard.
4. The engine prints a WARNING to stderr (interpreted by the
   operator as advisory, not blocking) and exits 0. The worker field
   still says `runner-a`. The dashboard now misattributes the work.

This is the same family of "worker field drift on re-claim" as
the open sibling
[goc-status-active-preserves-prior-worker-who-on-reclaim](../goc-status-active-preserves-prior-worker-who-on-reclaim/),
but a DISTINCT code path: that card is about the `active → open →
active` round-trip where `_auto_populate_worker` runs and
asymmetrically preserves only `worker.who`. THIS card is about the
`active → active` early-return where `_auto_populate_worker` is
never called and BOTH sub-fields are silently dropped.

The decision recorded on the sibling card constrains this one: if
the sibling resolves "refresh both sub-fields on re-claim," this
card's early-return must also be amended to honor the override
flags. Hence the `advanced_by` edge.

## Decision required

Three credible fix paths:

1. **Honor the flags on no-op re-claim.** Drop the early-return when
   `--worker-who` or `--worker-where` is non-None and `new_status ==
   "active"`; fall through to the `_auto_populate_worker` path so
   the override takes effect. Keep the racing-claim WARNING as an
   advisory.
2. **Exit non-zero when overrides are passed against an active
   card.** Treat `goc status X active --worker-who Y` on an
   already-active X as a probable mistake; print "X already active;
   release via `goc status X open` first" and exit 2.
3. **Keep current silent-drop; document it.** Update the
   `--worker-who` / `--worker-where` help text to say "ignored when
   the target is already in the requested status." The user-facing
   surface becomes truthful even though the behavior is unchanged.

The choice should align with whatever the sibling
[goc-status-active-preserves-prior-worker-who-on-reclaim](../goc-status-active-preserves-prior-worker-who-on-reclaim/)
records — these are two manifestations of the same underlying
question ("what does `goc status active` mean when worker context
has changed?").

## Fix

Mechanical edit at `engine.py:3972-3981` once the decision is
recorded. The simplest form of option (1):

```python
if prior == new_status:
    if new_status == "active":
        worker_overrides = (
            args.worker_who is not None or args.worker_where is not None
        )
        if not worker_overrides:
            print(
                f"WARNING: {title}: already active — possible racing claim;"
                f" check `goc --status active` before proceeding",
                file=sys.stderr,
            )
            return
        # fall through to mutate worker only
    else:
        print(f"{title}: already {new_status}; nothing to do")
        return
```

Then the mutation block at `engine.py:3997-4003` would need a guard
so it only writes `status` / `closed_at` when actually transitioning,
and only writes worker when on the active branch.
