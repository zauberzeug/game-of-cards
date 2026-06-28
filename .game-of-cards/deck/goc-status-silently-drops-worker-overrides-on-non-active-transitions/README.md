---
title: goc-status-silently-drops-worker-overrides-on-non-active-transitions
summary: "`goc status <t> {open|disproved|superseded} --worker-who alice --worker-where feature/foo` silently produces no worker mutation. `_cmd_status` only invokes `_auto_populate_worker` inside `if new_status == \"active\":` (engine.py:4003-4004), so the flags are read off `args` (engine.py:3955-3956) and then dropped on every non-active transition. The argparser at engine.py:2621-2624 advertises both flags with no restriction on `new_status`, unlike `--by` which has an explicit `new_status != \"superseded\"` reject at engine.py:3958-3964. Sibling family of `goc-status-active-discards-worker-overrides-when-target-already-active` (which covers the `prior == new_status == active` early-return path) — this one covers the `new_status != active` code-path branch."
status: open
stage: null
contribution: medium
created: "2026-05-29T21:24:23Z"
closed_at: null
human_gate: decision
advances:
  - mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] PROCESS: decision recorded in `## Decision required` (honor the override flags on non-active transitions and write the worker block; OR keep silent-drop and document it in `--worker-who` / `--worker-where` help text; OR exit non-zero with a "--worker-who/--worker-where only apply with new_status=active" diagnostic — the same shape `--by` already uses for the `superseded` constraint at engine.py:3958-3964).
  - [ ] TDD: `reproduce.py` exits zero — chosen behavior matches expectation across the matrix (`new_status ∈ {open, disproved, superseded}` × override-flags-set).
  - [ ] TDD: a unittest under `tests/` exercises `goc status <t> disproved --worker-who <new>` on an open card and asserts the chosen behavior so a future `_cmd_status` refactor cannot reintroduce the silent drop.
  - [ ] MECHANICAL: argparser help text at engine.py:2621-2624 (`--worker-who`, `--worker-where`) reads consistently with the chosen behavior.
  - [ ] PROCESS: `uv run goc validate` clean; `uv run python -m unittest discover -s tests` green.
---

# `goc status` silently drops `--worker-who` / `--worker-where` on non-active transitions

## Location

- Worker-update path that only runs on `active`: `goc/engine.py:4003-4004`
- Args parsed but never reached: `goc/engine.py:3955-3956`
- Argparser that advertises the flags without restriction: `goc/engine.py:2621-2624`
- The sister `--by` validator that DOES reject for the wrong `new_status`: `goc/engine.py:3958-3964`

## What's broken

`_cmd_status` reads the override flags off `args` unconditionally:

```python
3955:    worker_who = args.worker_who
3956:    worker_where = args.worker_where
```

But applies them only inside the `active` branch, near the end:

```python
4003:    if new_status == "active":
4004:        text = _auto_populate_worker(text, t, worker_who, worker_where)
```

There is no else branch, no warning, and no error. For `new_status ∈
{open, disproved, superseded}` the flags are dropped on the floor.
This is structurally asymmetric with the `--by` flag, which has an
explicit reject when used outside the `superseded` transition just a
few lines above:

```python
3958:    if successor is not None and new_status != "superseded":
3959:        print(
3960:            f"ERROR: --by is only valid with new_status=superseded "
3961:            f"(got new_status={new_status!r})",
3962:            file=sys.stderr,
3963:        )
3964:        sys.exit(2)
```

The argparser, meanwhile, advertises both flags as if they apply on
every status transition:

```python
2621:    p_status.add_argument("--worker-who", default=None,
2622:                          help="Override worker.who identity.")
2623:    p_status.add_argument("--worker-where", default=None,
2624:                          help="Override worker.where branch or path for this claim.")
```

## Empirical evidence

`reproduce.py` builds a temp deck, files a card in `status: open` (no
`worker` field), then runs `goc status <t> disproved --worker-who alice
--worker-where feature/foo`. Output (excerpt):

```
before: status=open, worker=<absent>
goc status probe-status-worker disproved --worker-who alice --worker-where feature/foo
  → probe-status-worker: open → disproved (exit 0; no error about dropped flags)
after:  status=disproved, worker=<absent>     <-- flags silently dropped

DEFECT REPRODUCED
```

(The same shape reproduces with `new_status=open` from `active`, and
with `new_status=superseded --by <other>` — every non-active transition
drops the override.)

## Why it matters

Three reachability paths:

1. **CI / orchestration runners.** A scheduled `pull-card` /loop or a
   GitHub Action that flips a card to `disproved` after a failed
   automated repro wants to attribute the disproval to a specific
   worker identity (`goc status <t> disproved --worker-who ci-runner
   --worker-where <branch>`). The runner's invocation succeeds silently
   without writing the attribution — the `worker:` field stays at
   whatever the prior claimant set it to, mis-attributing the disproval.

2. **Manual supersession with a different attestor.** When a human
   supersedes one card with another (`goc status <old> superseded --by
   <new> --worker-who <attestor>`), the `--by` half is honored (the
   typed link is written) but the `--worker-who` half is dropped. The
   superseded card's `worker:` reflects the original claimant, not the
   superseder. The history is wrong.

3. **Mid-flip identity rewrite.** A worker reading their own deck
   discovers a card whose `worker.who` is stale (machine identity from
   a previous tenant, or an empty `{who: ""}` from the existing bug
   `worker-mapping-with-only-a-branch-emits-invalid-empty-who`) and
   tries to fix it by re-running `goc status <t> open --worker-who
   <real>`. The status flip is a no-op anyway (already open → again
   open), but they expected `--worker-who` to update the field. It
   doesn't, and the CLI says nothing.

The asymmetry between `--by` (validated, rejected with a clear error
when `new_status` is wrong) and `--worker-who` / `--worker-where`
(silently accepted, silently dropped) is the kind of API-contract
drift that the `meta-fix` family exists to surface — same family as
the recent `goc-decide-accepts-empty-decision-and-because-arguments`,
`goc-advance-claims-success-when-adding-an-already-existing-edge`,
and the sibling `goc-status-active-discards-worker-overrides-when-target-already-active`.

## Reachability path

Reachable without contrived input:

- The argparser at `engine.py:2621-2624` exposes both flags on every
  `new_status` choice (the `choices=` list at `engine.py:2613` is
  `MUTABLE_STATUS_VALUES` — all non-`done` statuses).
- `_cmd_status` accepts the args without ever rejecting them
  (`engine.py:3955-3956` just reads them).
- `_auto_populate_worker` is the only call site that consults them,
  guarded by `if new_status == "active"` (`engine.py:4003-4004`).
- The closure-path verb `goc done` has its own `_cmd_done` handler
  that doesn't accept the worker flags at all (separate code path).

Therefore: anyone running `goc status <t> <X>` with `<X> ∈ {open,
disproved, superseded}` and passing `--worker-who` or `--worker-where`
hits the drop. No contrived precondition required.

## Decision required

Three credible fixes:

### Option A — Apply the overrides on every transition

Pull the `_auto_populate_worker` call out of the `if new_status ==
"active"` branch so it runs whenever either flag is set:

```python
if worker_who is not None or worker_where is not None or new_status == "active":
    text = _auto_populate_worker(text, t, worker_who, worker_where)
```

Pros: the flags now mean what the help text says. CI runners and
manual identity rewrites work. Distinguishes the "no flag = no
mutation" case from the "flag = write".

Cons: `_auto_populate_worker` was designed around the claim ceremony
(auto-derive `who` from git config, `where` from current branch when
flags are absent). The body of the function may need a small refactor
to skip the auto-derivation path when only one of the two flags is
set (don't synthesize a branch on a disproval flip).

### Option B — Reject the flags on non-active transitions

Mirror the `--by` validator's shape:

```python
if (worker_who is not None or worker_where is not None) and new_status != "active":
    print(
        f"ERROR: --worker-who / --worker-where are only valid with "
        f"new_status=active (got new_status={new_status!r})",
        file=sys.stderr,
    )
    sys.exit(2)
```

Pros: API contract is consistent — the flags are advertised, and
when used in the wrong context the user gets a clear error instead
of silent drop. Matches the `--by` precedent. No semantic surprises
in `_auto_populate_worker`.

Cons: closes the door on Option A's CI / supersession-attestation
use cases. Users would have to do `goc status <t> disproved` then a
separate manual edit, or invoke a hypothetical future
`goc set-worker <t>` verb.

### Option C — Document the silent-drop in the help text

Leave the code, sharpen the help text:

```python
p_status.add_argument("--worker-who", default=None,
    help="Override worker.who identity (only applied when new_status=active; ignored otherwise).")
p_status.add_argument("--worker-where", default=None,
    help="Override worker.where branch or path for this claim (only applied when new_status=active; ignored otherwise).")
```

Pros: zero behavior change, smallest blast radius. Documents reality.

Cons: silent drops remain a violated user expectation in scripts —
the help text is only seen when invoking `--help`, not when the
script is run. Asymmetry with `--by` persists.

### Recommendation

Option B (reject) reads as the path of least surprise: it follows
the `--by` precedent already in the same function, the change is
mechanical, and the diagnostic is short. Option A is tempting but
opens a design surface around `_auto_populate_worker`'s
auto-derivation in non-claim contexts that this card doesn't budget
for. Gate stays `decision` until the human picks.

## Sibling cards / related family

- [`goc-status-active-discards-worker-overrides-when-target-already-active`](../goc-status-active-discards-worker-overrides-when-target-already-active/)
  — same flag-drop symptom, different code path (the `prior ==
  new_status == active` early-return at engine.py:3974-3983 fires
  *before* `_auto_populate_worker`). The two cards together cover
  the full set of `_cmd_status` paths where `--worker-who` /
  `--worker-where` are accepted and then dropped. Whichever decision
  this card lands on should land on its sibling too (consistency).
- [`worker-mapping-with-only-a-branch-emits-invalid-empty-who`](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/)
  — schema-level bug, separate but in the same neighborhood. A fix
  here that goes through `_auto_populate_worker` should not
  reintroduce the empty-`who` shape.

## Artifacts

- reproduce.py
