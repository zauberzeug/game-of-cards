---
title: blank-worker-overrides-write-cards-that-goc-validate-rejects
summary: "The worker write path applies no non-empty or emittability guard, so `goc new --worker` and `goc status <title> active --worker-who/--worker-where` accept a whitespace-only value, exit 0 with a success line, and write frontmatter that `goc validate` immediately rejects — the engine emitting state its own validator refuses, which turns this repo's validate-gated CI red. The same two flags also reach `_yaml_inline` unguarded, so a line-break value raises a raw FrontmatterError traceback instead of the CLI's ERROR + exit 2 contract."
status: done
stage: null
contribution: medium
created: "2026-08-07T05:22:28Z"
closed_at: "2026-08-07T05:32:07Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits 1 — all four doors are closed (three refuse with `ERROR:` + exit 2 and write nothing; the line-break door no longer leaks a traceback).
  - [x] TDD: A regression test asserts `goc new --worker`, `goc status <t> active --worker-who`, and `--worker-where` each exit 2 with an `ERROR:` line on an empty, whitespace-only, or line-break value, and that the target card's `worker` field is unchanged on disk.
  - [x] TDD: The same test holds the accepted shapes — an ordinary `who`, a `{who, where}` pair, and an omitted flag — so the guard cannot widen into a false refusal.
  - [x] MECHANICAL: `uv run goc validate` clean and `uv run python -m unittest discover -s tests` green (modulo the pre-existing `test_canonical_tag_rows` red tracked by [regression-suite-red-on-main-over-the-unverified-tag-row](../regression-suite-red-on-main-over-the-unverified-tag-row/)).
worker: {who: "claude[bot]", where: main}
---

# Blank worker overrides write cards that `goc validate` rejects

## Summary

The `worker` write path applies no non-empty or emittability guard. `goc new
--worker "   "` and `goc status <title> active --worker-who "   "` /
`--worker-where "   "` each accept the value, exit 0 with a success line, and
write frontmatter that `goc validate` immediately refuses — the engine emitting
state its own validator rejects. The same two `goc status` flags reach
`_yaml_inline` unguarded, so a line-break value raises a raw `FrontmatterError`
traceback instead of the CLI's `ERROR:` + exit 2 contract.

## Location

Line numbers below are as-of the defect (commit `4a42e44c`); the fix inserted a
helper at `engine.py:4703` and shifted everything under it by ~34 lines. Current
positions are in "Fix (applied)".

- `goc/engine.py:5688-5697` — `_cmd_new`'s only `--worker` guard (line breaks; no
  whitespace check).
- `goc/engine.py:5390-5391`, `5401-5402` — `_auto_populate_worker` assigns
  `worker_who` / `worker_where` straight from the flags, unvalidated.
- `goc/engine.py:5425-5428` — the same function hands both to `_yaml_inline`.
- `goc/engine.py:5523` — `_cmd_status` calls it on every `active` transition.
- `goc/engine.py:1770-1787` — `validate_card`, which rejects exactly what those
  writers produce.

## What's broken

Two closed cards deliberately tightened the *validator* to reject blank worker
values — [validate-accepts-whitespace-only-worker-as-non-empty](../validate-accepts-whitespace-only-worker-as-non-empty/)
and [validate-accepts-whitespace-only-worker-where-as-non-empty](../validate-accepts-whitespace-only-worker-where-as-non-empty/).
Both are `done`. `validate_card` now reads:

```python
if isinstance(worker, str):
    if not worker.strip():
        errors.append(f"{t.title}: worker: must not be empty or whitespace-only")
...
    if "where" in worker and (
        not isinstance(worker.get("where"), str) or not worker["where"].strip()
    ):
        errors.append(
            f"{t.title}: worker: 'where' must be a non-empty, non-whitespace string"
        )
```

The **writers were never brought into line.** `_auto_populate_worker` takes the
flags verbatim:

```python
    if worker_who is not None:
        who = worker_who
...
    if worker_where is not None:
        where: str | None = worker_where
```

and its only emptiness check is falsiness, which a whitespace string passes:

```python
    if not who:
        return text
```

The asymmetry is sharpest inside `_cmd_new`, where the two guards sit **eleven
lines apart**. `--summary` gets a whitespace check (`engine.py:5667-5669`):

```python
        if not summary.strip():
            print("ERROR: --summary must not be empty or whitespace-only", file=sys.stderr)
            sys.exit(2)
```

`--worker` gets only a line-break check (`engine.py:5691-5697`) — added by the
immediately preceding card,
[goc-new-leaves-an-empty-card-directory-when-summary-or-worker-carries-a-line-break](../goc-new-leaves-an-empty-card-directory-when-summary-or-worker-carries-a-line-break/),
which fixed the emittability half of this same seam for `goc new` and left both
the whitespace half and all of `goc status` untouched:

```python
    if worker and _contains_line_break(worker):
```

So each of the three flags is missing a guard its immediate neighbour already
has, and `goc status`'s two flags are missing both.

## Empirical evidence

`uv run python .game-of-cards/deck/blank-worker-overrides-write-cards-that-goc-validate-rejects/reproduce.py`
on a clean checkout, in a throwaway git repo with `GOC_WORKER` cleared:

```
=== Door A: goc new --worker '   ' ===
  exit               : 0
  frontmatter written: 'worker: "   "'
  goc validate says  : ['ERROR: door-a-new-worker: worker: must not be empty or whitespace-only']

=== Door B: goc status <t> active --worker-who '   ' ===
  exit               : 0
  stdout             : ['door-b-who: open → active']
  frontmatter written: 'worker: "   "'
  goc validate says  : ['ERROR: door-b-who: worker: must not be empty or whitespace-only']

=== Door C: goc status <t> active --worker-where '   ' ===
  exit               : 0
  frontmatter written: 'worker: {who: bob, where: "   "}'
  goc validate says  : ["ERROR: door-c-where: worker: 'where' must be a non-empty, non-whitespace string"]

=== Door D: goc status <t> active --worker-who $'a\rb' ===
  exit               : 1
  traceback leaked   : True
  last stderr line   : 'goc.engine.FrontmatterError: frontmatter scalar contains a line-break character the vendor'

==============================================================
DEFECT REPRODUCED: all four doors bypass the worker write-path guards.
```

Door B is the load-bearing one: the verb prints `open → active`, the claim
lands, and the deck is left validate-red by the mutation that reported success.

After the fix, the same probe reports every door closed (it inverts, exiting 1):

```
=== Door A: goc new --worker '   ' ===
  exit               : 2
  frontmatter written: '<no README written>'
  goc validate says  : []

=== Door B: goc status <t> active --worker-who '   ' ===
  exit               : 2
  stdout             : []
  frontmatter written: '<no worker field>'
  goc validate says  : []

=== Door C: goc status <t> active --worker-where '   ' ===
  exit               : 2
  frontmatter written: '<no worker field>'
  goc validate says  : []

=== Door D: goc status <t> active --worker-who $'a\rb' ===
  exit               : 2
  traceback leaked   : False
  last stderr line   : 'ERROR: --worker-who must not contain a line break; the worker field has no multi-line form'
```

## Why it matters

**Reachability.** `worker` is the one frontmatter field whose value is routinely
machine-supplied rather than typed by an author. `Skill(card-schema)` documents
`GOC_WORKER` as the env var for "runner-specific queue views", and CI templating
is the ordinary door: `--worker-who "$RUNNER_NAME"` where the variable expands to
whitespace, a trailing space left in a job template, or a value read from a file
via `--worker-who "$(cat identity)"` — command substitution strips a trailing LF
but not a trailing CR, which is door D verbatim. None of these require anyone to
deliberately type a blank flag.

**Consequence.** `goc status <t> active` is the single most common mutation in
the autonomous loop — every `Skill(pull-card)` run begins with one. A claim that
writes validate-red frontmatter poisons the deck at the exact moment a worker
picks up work, and in this repo `goc validate` gates CI (`.github/workflows/ci.yml`),
so the next push goes red with an error pointing at a card whose author did
nothing wrong. Recovery means hand-editing frontmatter, because the verb that
wrote it reported success and left no trace.

This is the *corrupting-write* variant of the family aggregated by
[mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success](../mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success/).
It is filed standalone rather than as a ninth child of that epic on purpose:
that epic is decision-gated on choosing a *shared failure shape* for verbs that
silently no-op, and its DoD is written against a roster of eight. Here there is
no shape to choose — a writer that emits what its own validator refuses has one
correct behaviour, and the precedent (`--summary`, eleven lines up) already fixes
the wording and the exit code. Distinct also from
[goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field](../goc-new-stamps-goc-worker-queue-filter-into-authored-worker-field/)
(wrong value *source*, via a shared argparse dest) and
[worker-mapping-with-only-a-branch-emits-invalid-empty-who](../worker-mapping-with-only-a-branch-emits-invalid-empty-who/)
(re-emit inventing `who: ""` from an already-malformed card). Both are about
values the flags never touched; this card is about the flags themselves.

## Fix (applied)

`_reject_invalid_worker_flag(flag, value)` (`goc/engine.py:4703-4735`) validates
a worker-flag value at the CLI boundary, matching the `--summary` guard's
`ERROR:` + exit 2 shape. It sits beside `_validate_commit_flags`, the other
pre-write entry guard, and borrows both predicates from the components that
enforce them so the boundary check cannot drift from what actually round-trips:

- **whitespace/empty** — refuses when `not value.strip()`, the same predicate
  `validate_card` applies at `engine.py:1773`/`1781`, so the writer and the
  validator cannot disagree about what is a legal worker.
- **line break** — refuses when `_contains_line_break(value)`, the expression
  `_cmd_new` already applied to `--worker`. `worker` has no block-scalar form
  (`_emit_worker` sends every scalar through `_yaml_inline`), so LF is
  unemittable here too — no `.replace("\n", "")` carve-out, unlike `--summary`.

Call sites:

- `_cmd_new` (`engine.py:5729-5736`) — replaces the line-break-only guard.
  Guarded by `if worker:` because `new --worker` shares its argparse dest with
  the global `--worker` queue filter (default `$GOC_WORKER`), where `""` is the
  "no worker supplied" sentinel the write below already treats as absent.
- `_cmd_status` (`engine.py:5479-5484`) — both flags checked at verb entry,
  above every disk read. They default to `None` when omitted, so any string
  there — `""` included — is explicit user input. A refusal now leaves the card
  byte-identical: no status flip, no worker stamp, no cleared draft flag.
