---
title: goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field
summary: "`goc new`'s `--worker` uses `argparse.SUPPRESS` and shares the default dest `worker` with the global `--worker` queue filter (whose default is `$GOC_WORKER`). So a bare `goc new` run with `GOC_WORKER` or global `--worker` set stamps that triage-filter value into the new card's authored `worker` field. Fix: give `new --worker` a distinct dest, mirroring the `advances_wire`/`advanced_by_wire` remedy at engine.py:2830-2833. Decision-gated on the intended contract."
status: open
stage: null
contribution: medium
created: "2026-06-03T04:41:06Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] PROCESS: confirm the intended contract via `## Decision required` — a bare `goc new` should leave `worker` unset even when `GOC_WORKER` / global `--worker` is present (vs. auto-attributing the runner); record the choice via `Skill(decide-card)` (lowers the gate to `none`).
  - [ ] TDD: reproduce.py exits zero — `GOC_WORKER=alice goc new x` (and `goc --worker bob new y`) produces a card with no `worker` field, while `goc new z --worker carol` still writes `worker: carol`.
  - [ ] MECHANICAL: give `goc new`'s `--worker` a distinct argparse dest (mirroring the `advances_wire` / `advanced_by_wire` remedy at engine.py:2830-2833) so the global filter dest can no longer bleed into `_cmd_new`; read that dest in `_cmd_new`.
  - [ ] PROCESS: a regression test lands in `tests/`; the existing `tests/test_global_flag_collision.py` tripwire stays green (a distinct dest removes `new --worker` from the parent-collision set).
  - [ ] PROCESS: `uv run python -m unittest discover -s tests` stays green; `uv run goc validate` clean.
---

# `goc new` stamps the `GOC_WORKER` queue filter into the authored `worker` field

## Location

- `goc/engine.py:2734` — the **global** `--worker` flag, documented and
  intended as a queue/triage **filter**, with the env var as its default:

  ```python
  parser.add_argument("--worker", default=os.environ.get("GOC_WORKER"),
                      help="Filter by worker.who (substring match). Also read from GOC_WORKER env var.")
  ```

- `goc/engine.py:2834` — `goc new`'s own `--worker`, declared with
  `default=argparse.SUPPRESS` and sharing the default dest `worker`:

  ```python
  p_new.add_argument("--worker", default=argparse.SUPPRESS,
                     help="Worker designation (overrides global --worker / $GOC_WORKER; ...)")
  ```

- `goc/engine.py:4377, 4427-4428` — `_cmd_new` reads that dest and
  writes it into the new card's frontmatter:

  ```python
  worker = args.worker          # 4377
  ...
  if worker:                    # 4427
      fm["worker"] = worker     # 4428
  ```

## What's broken

`new`'s `--worker` uses `SUPPRESS`, so when the user does **not** pass
`--worker` to `new`, the subparser leaves the attribute alone and the
**global** `--worker` value — whose default is `os.environ.get("GOC_WORKER")`
— flows straight into `args.worker` and gets stamped onto the card as
its authored worker designation.

The global `--worker` is documented (engine.py:2735, AGENTS.md) as a
**read-side queue filter** for runner-scoped views; the worker field
on a card is a **write-side authorship designation**. The two share a
dest, and the filter value leaks into the authored field.

## Empirical evidence

In a throwaway deck (`reproduce.py` automates this):

```
GOC_WORKER=alice goc new x   -> worker: alice      (should be unset)
goc --worker bob new y       -> worker: bob        (should be unset)
goc new z                    -> (no worker field)  (correct control)
goc new w --worker carol     -> worker: carol      (correct — explicit)
```

## Why it matters

Reachability path: the autonomous-runner scenario is *exactly* the
`GOC_WORKER`-is-set case — the env var exists to scope a runner's read
queue. Any card filed by `goc new` on such a runner (e.g. an
audit-deck or pull-card session filing a finding) silently acquires
the runner's identifier as its authored worker, mis-attributing
provenance on every filing. It is a regression of the SUPPRESS fix in
`global-cli-flags-silently-dropped-by-subcommand-flag-defaults`:
correct for `triage` (worker is a *filter* there), wrong for `new`
(worker is an *authored field* there) because `new` overloads the
same dest. The contract card `add-worker-field-and-filter-to-cards`
states "Cards filed without `--worker` have no worker designation,"
and `new`'s own help text promises its `--worker` *overrides*
`$GOC_WORKER` — i.e. absence should not inherit.

## Proposed fix

Give `goc new`'s `--worker` a distinct dest (e.g. `worker_designation`)
so the global filter dest cannot bleed in — the same "distinct dests"
remedy already applied to `--advances` / `--advanced-by` on `goc new`
(engine.py:2830-2833) — and read that dest in `_cmd_new`. The
`tests/test_global_flag_collision.py` tripwire stays green because a
distinct dest removes `new --worker` from the parent-collision set
entirely.

## Decision required

The fix mechanism is determined, but the *intended behavior* is a
taste call worth confirming before changing it:

- **(a) Bare `goc new` under `GOC_WORKER` leaves `worker` unset**
  (treat the leak as a bug). Matches the documented filter-vs-field
  split and the contract card's "no worker designation without
  `--worker`."
- **(b) Auto-attribute the runner** — keep stamping `GOC_WORKER` as the
  authored worker on the theory that "who filed it" is useful
  provenance, and instead *document* that `GOC_WORKER` doubles as a
  filing identity.

Option (a) is the strong default (it honors the existing docs and the
`--worker overrides $GOC_WORKER` help promise); (b) would require
rewriting that contract. Record the choice via `Skill(decide-card)`.
