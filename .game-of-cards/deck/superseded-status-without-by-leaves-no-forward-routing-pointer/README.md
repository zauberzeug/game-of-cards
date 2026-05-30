---
title: superseded-status-without-by-leaves-no-forward-routing-pointer
summary: "`goc status <card> superseded` accepts no `--by` argument and the card lands with `status: superseded` and no `superseded_by` link. `goc validate` reports OK because the check at engine.py:1255-1260 only enforces the inverse direction (non-empty `superseded_by` implies `status: superseded`), not the contract that AGENTS.md describes as set atomically. Cold readers following the forward routing pointer have nowhere to go."
status: done
stage: null
contribution: high
created: "2026-05-29T15:13:43Z"
closed_at: "2026-05-30T14:20:56Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `deck/<title>/reproduce.py` exits zero and asserts that `goc status <card> superseded` with no `--by` is rejected (or that the resulting card fails `goc validate` with a `superseded_by required` error).
  - [x] PROCESS: decide fix path — CLI input guard (require `--by` when `new_status == "superseded"`), validator check (`status: superseded` requires non-empty `superseded_by`), or both. Record reasoning in log.md.
  - [x] TDD: a regression test in `tests/` exercises the chosen guard.
  - [x] MECHANICAL: `goc validate` clean across the deck; plugin mirrors regenerated (`python scripts/sync_plugin_assets.py`); pre-commit clean.
  - [x] PROCESS: confirm `goc done <card>` and `_cmd_status` agree on the invariant — `done` already auto-commits closure data, but `superseded` should not be reachable without a successor.
worker: {who: "claude[bot]", where: main}
---

# Superseded status without `--by` leaves no forward routing pointer

## Location

`goc/engine.py:1255-1260` (validator) and `goc/engine.py:3948-4018`
(`_cmd_status`).

## What's broken

The CLI accepts `goc status <card> superseded` with no `--by`
argument. The card lands as `status: superseded` with no
`superseded_by` field set. `goc validate` reports `OK`. A cold reader
walking the supersession graph forward to find what replaced the
card hits a dead end.

The validator at `goc/engine.py:1255-1260`:

```python
superseded_by = fm.get("superseded_by") or []
if isinstance(superseded_by, list) and superseded_by and status_value != "superseded":
    errors.append(
        f"{t.title}: superseded_by: non-empty requires status: superseded "
        f"(status={status_value!r})"
    )
```

The check is **asymmetric**: it enforces "non-empty `superseded_by`
implies `status: superseded`" but never the inverse — "`status:
superseded` implies non-empty `superseded_by`".

The CLI at `goc/engine.py:3957-3963` only refuses `--by` for
non-superseded targets:

```python
if successor is not None and new_status != "superseded":
    print(
        f"ERROR: --by is only valid with new_status=superseded "
        f"(got new_status={new_status!r})",
        file=sys.stderr,
    )
    sys.exit(2)
```

There is no inverse check that requires `--by` when
`new_status == "superseded"`.

## Contradicted documentation

`AGENTS.md` "deck as scheduler vs deck as record" states:

> supersession records a typed `superseded_by` / `supersedes` link
> (set atomically by `goc status <old> superseded --by <new>`) so a
> reader landing on a `superseded` card can be routed forward
> without parsing prose.

"Set atomically" implies the link is part of the supersession state
transition, not optional. The shipped CLI accepts the transition
without the link and the validator does not catch it.

## Empirical evidence

Reproduced in a clean checkout at `/tmp/goc-repro`:

```text
$ uv run goc new test-card-a
created .game-of-cards/deck/test-card-a/
$ uv run goc status test-card-a active
test-card-a: open → active
$ uv run goc status test-card-a superseded
test-card-a: active → superseded
$ cat .game-of-cards/deck/test-card-a/README.md | head -15
---
title: test-card-a
summary: ""
status: superseded
stage: null
contribution: medium
created: "2026-05-29T15:12:59Z"
closed_at: "2026-05-29T15:13:02Z"
human_gate: decision
advances: []
advanced_by: []
tags: []
...
$ uv run goc validate
OK  test-card-a
```

Note the missing `superseded_by` field and the clean validate
output. A `goc show test-card-a` lands a cold reader on a card that
says "I was replaced" without saying by what.

## Why it matters

The supersession link is the **deck-as-record** axis: it lets a
reader who lands on a closed card discover the successor without
parsing prose. The closed-predecessor card
`auto-publish-npm-and-clawhub-on-tag-push` in this repo's own deck
points forward to `find-single-trigger-release-flow-for-all-three-registries`
through `superseded_by`; without that pointer, a reader has to
either grep `log.md` or guess.

Reachability path: every consumer of `goc status` is a candidate
producer of the offending state. Specifically, `_cmd_status` is the
only writer that touches `status: superseded`; an authored card
cannot have a closed_at timestamp on filing, so the CLI is the sole
source of the orphan transition. The CLI is the right place to
enforce the contract, and the validator is the right place to
verify it for hand-edited frontmatter.

A related card `mutual-supersession-passes-validation-and-creates-forward-pointer-cycle`
(done) plugged the *cycle* hole in this same graph; this card plugs
the *missing-edge* hole.

## Decision

*Resolved 2026-05-30T13:36:43Z:* Both: a CLI guard in _cmd_status refuses 'goc status <card> superseded' when --by is absent, AND the validator rejects status:superseded with empty superseded_by

*Reasoning:* defense-in-depth — the CLI guard fails fast at the input boundary with a clear message while the validator catches hand-edited and direct-frontmatter drift, matching the same dual-gate pattern that goc done's DoD-gate + goc validate already share

## Fix sketch (independent of the chosen path)

For the validator-side check, add after `goc/engine.py:1260`:

```python
if status_value == "superseded" and not superseded_by:
    errors.append(
        f"{t.title}: status: superseded requires non-empty superseded_by "
        f"(forward routing pointer)"
    )
```

For the CLI-side guard, add after `goc/engine.py:3963`:

```python
if new_status == "superseded" and successor is None:
    print(
        f"ERROR: status superseded requires --by <successor> "
        f"(the typed forward routing pointer)",
        file=sys.stderr,
    )
    sys.exit(2)
```

A regression test in `tests/` would (a) call the validator on a
hand-crafted fixture frontmatter with `status: superseded` and
empty `superseded_by`, and (b) shell out to the CLI to confirm
`goc status <c> superseded` without `--by` exits non-zero.
