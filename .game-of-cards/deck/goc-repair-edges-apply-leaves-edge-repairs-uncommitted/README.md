---
title: goc-repair-edges-apply-leaves-edge-repairs-uncommitted
summary: "`goc repair-edges --apply` writes the missing reverse half-edges to disk via `_mutate_pair` but never calls `_git_auto_commit`. Every other state-mutation verb (advance, unadvance, status, decide, done, wait) auto-commits by default and exposes `--commit` / `--no-commit` to override. repair-edges' subparser does not expose either flag, so the repair always leaves the working tree dirty — a parallel agent's later auto-commit may silently bundle the repair into an unrelated commit, and the human reviewer sees no record of what changed."
status: open
stage: null
contribution: medium
created: "2026-05-29T20:04:05Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - goc-move-leaves-cross-reference-rewrites-uncommitted
  - goc-migrate-list-style-leaves-bulk-rewrite-uncommitted
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `deck/<title>/reproduce.py` exits zero and asserts that after `goc repair-edges --apply` the modified card README is committed (HEAD advanced, working tree clean), matching `goc advance --by` behavior on the same fixture.
  - [ ] PROCESS: decide fix path — add `--commit` / `--no-commit` flags + `_git_auto_commit` call (matches the family), or document repair-edges as an intentional non-committing audit-then-stage verb. Record reasoning in log.md.
  - [ ] TDD: regression test in `tests/` exercises the chosen behavior end-to-end.
  - [ ] MECHANICAL: `goc validate` clean across the deck; plugin mirrors regenerated; pre-commit clean.
  - [ ] PROCESS: sweep `_cmd_move` for the same shape — its text-rewrite phase also writes files without staging or committing. File a sibling card if confirmed, or close the gap in this card if the chosen fix generalizes.
---

# `goc repair-edges --apply` leaves edge repairs uncommitted

## Location

- `goc/engine.py:2685-2694` (subparser — no `--commit` / `--no-commit`).
- `goc/engine.py:4252-4306` (`_cmd_repair_edges` — no `_git_auto_commit` call).
- `goc/engine.py:4180-4193` (`_mutate_pair` — the disk-write helper repair-edges shares with `advance` / `unadvance`).

## What's broken

Every other state-mutation verb in the engine auto-commits by default and
exposes a `--commit` / `--no-commit` pair. `_cmd_advance` is representative
(`engine.py:4382-4400`):

```python
def _cmd_advance(args):
    ...
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
    print(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
    commit_policy = _commit_override(commit, no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} advances {title}"):
            print("  committed")
```

`_cmd_repair_edges` calls the same `_mutate_pair` helper but skips the
auto-commit tail entirely (`engine.py:4283-4306`):

```python
repaired = 0
structural = []
for edge in half_edges:
    current_cards = load_all_cards()
    problem = _repair_edge_cycle_problem(edge, current_cards)
    if problem:
        structural.append((edge, problem))
        continue
    _mutate_pair(edge.ref, edge.src, edge.inverse, edge.field, add=True)
    print(f"repaired: {edge.message}")
    repaired += 1

if repaired:
    print(f"Repaired {repaired} half-edge(s).")
else:
    print("No half-edges repaired.")
_print_structural_edge_problems(structural)
if structural:
    sys.exit(1)
```

The subparser at `engine.py:2685-2694` is similarly stripped:

```python
p_repair_edges = subparsers.add_parser(
    "repair-edges",
    help="Preview or repair asymmetric advances/advanced_by edges.",
)
p_repair_edges.add_argument(
    "--apply",
    action="store_true",
    help="Write missing reverse edges. Default is preview-only.",
)
```

No `--commit`, no `--no-commit`, no `auto_commit_enabled` check.

## Empirical evidence

A clean test repo with one deliberately-introduced half-edge
(`foo.advances: [bar]` but `bar.advanced_by: []`):

```text
$ uv run goc repair-edges --apply
repaired: foo: advances contains 'bar' but bar.advanced_by is missing 'foo' (half-edge)
Repaired 1 half-edge(s).

$ git status --short
 M .game-of-cards/deck/bar/README.md

$ git log --oneline | head -1
55f036e introduce half-edge       # HEAD unchanged
```

Compare against `goc advance` on the same fixture (after reverting):

```text
$ uv run goc advance foo --by baz
advance: foo.advanced_by += baz; baz.advances += foo
  committed

$ git log --oneline | head -1
7280648 deck: baz advances foo    # HEAD advanced
```

See `reproduce.py` for the runnable check.

## Why it matters

Reachability is direct: the pre-commit hook runs `goc validate`, which
reports half-edges and prints `Run 'goc repair-edges --apply' to fix.`
(`engine.py:2920`). Anyone following that hint, or any `/loop` agent
running `repair-edges --apply` as part of routine cleanup, leaves the
working tree dirty.

Two concrete failure modes:

1. **Silent bundling under parallel agents.** AGENTS.md "Parallel-Agent
   Commit Safety" warns that another agent may be in its commit
   window. `_git_auto_commit` uses explicit pathspecs, so it won't
   pick up the repair, but a manual `git add -A` or a parallel
   agent's broader staging (the AGENTS.md guidance says "stage only
   explicit file paths," but humans and other tools do not always
   comply) silently absorbs the repair into an unrelated commit.

2. **Lost work under the closure-on-integration policy.** Cards
   closed via `goc done` require HEAD reachable from `origin/main`
   (`_enforce_closure_on_integration_or_exit`). A repair-edges run
   between `done` and `push` leaves uncommitted files that don't
   reach main on the next push, then the next pull-card session
   re-runs `validate`, sees the same half-edge, and the cycle
   repeats — unless someone notices the dirty tree and commits by
   hand.

This is the same family as the recent `meta-fix` cards
(`goc-advance-claims-success-when-adding-an-already-existing-edge`,
`goc-unadvance-claims-success-when-removing-a-non-existent-edge`,
`goc-attest-mutates-log-md-on-already-closed-cards`,
`goc-quality-pass-mutates-summary-and-dod-on-terminal-status-cards`):
disk-mutating verbs that diverge from the shared `_mutate_pair` /
`_git_auto_commit` / `_commit_override` contract the rest of the engine
follows.

## Decision required

Two credible fix paths; the choice affects how aggressively `validate`
should advertise the `repair-edges --apply` remediation hint.

### Option A — make repair-edges follow the family contract (recommended)

Add `--commit` / `--no-commit` to the subparser; after the
`_mutate_pair` loop succeeds, build a `commit_targets` list from the
touched card dirs and call `_git_auto_commit(commit_targets,
f"deck: repair {repaired} half-edge(s)")` gated on
`auto_commit_enabled(commit_policy)`.

Pros: matches `advance` / `unadvance` / `status` / `decide` / `wait` /
`done`; the `validate` hint stays safe under autonomous agents; one
commit per `--apply` run gives a reviewable record of what was
repaired.

Cons: bundles N repairs into one commit (vs. N commits if each
repair were its own auto-commit), which is a deliberate trade-off
the family does NOT make elsewhere — each `goc advance` is its own
commit. If per-repair commits are wanted, the loop body needs the
commit call inside it.

### Option B — document repair-edges as an intentional audit-then-stage verb

Update `validate`'s remediation hint and the `card-schema` /
`advance-card` skills to clarify that `repair-edges --apply` writes
to disk but does not commit; the operator is expected to stage and
commit the result themselves.

Pros: zero engine change; preserves the "the operator decides when
the repair becomes history" framing.

Cons: rest of the engine does not behave this way; autonomous
agents that follow `validate`'s hint without reading the skill body
will continue to leave dirty trees.

### Recommendation

Option A. The `meta-fix` family pattern (every disk-mutating verb
auto-commits by default with a `--no-commit` opt-out) is already
codified across six verbs; making `repair-edges` the seventh restores
the invariant the rest of the engine carries.

## Fix sketch (Option A)

```python
# engine.py around 2685
p_repair_edges = subparsers.add_parser("repair-edges", ...)
p_repair_edges.add_argument("--apply", action="store_true", ...)
p_repair_edges.add_argument("--commit", action="store_true",
                            help="Force auto-commit for this repair run.")
p_repair_edges.add_argument("--no-commit", action="store_true",
                            help="Skip auto-commit for this repair run.")

# engine.py around 4296 — after the for-loop, before the structural print
touched: list[Path] = []
for edge in half_edges:
    ...
    _mutate_pair(edge.ref, edge.src, edge.inverse, edge.field, add=True)
    touched.extend([DECK_DIR / edge.ref, DECK_DIR / edge.src])
    print(f"repaired: {edge.message}")
    repaired += 1

if repaired:
    print(f"Repaired {repaired} half-edge(s).")
    commit_policy = _commit_override(args.commit, args.no_commit)
    if auto_commit_enabled(commit_policy):
        if _git_auto_commit(touched, f"deck: repair {repaired} half-edge(s)"):
            print("  committed")
```

## Sibling sweep

`_cmd_move` at `engine.py:4487-4544` exercises a similar disk-write
path: it uses `git mv` (which stages the directory rename) but the
subsequent `_move_rewrite_tracked_files` writes to README.md / log.md
across the repo without staging or committing those rewrites. The
subparser at `engine.py:2697-2703` also does not expose `--commit` /
`--no-commit`. The DoD `PROCESS:` item flags this for a follow-up
card if Option A's fix does not generalize to cover move.
