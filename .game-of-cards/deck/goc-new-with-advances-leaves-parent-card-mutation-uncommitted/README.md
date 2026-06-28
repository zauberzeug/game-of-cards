---
title: goc-new-with-advances-leaves-parent-card-mutation-uncommitted
summary: "`goc new <child> --advances <parent>` writes the parent's `advanced_by` edge to disk but never commits it, leaving the parent README as ambient `M` in the worktree. An agent that follows AGENTS.md's explicit-pathspec rule and commits only the new card directory ships a half-edge — exactly the integrity defect `goc repair-edges` exists to clean up."
status: done
stage: null
contribution: high
created: "2026-05-29T16:21:00Z"
closed_at: "2026-05-30T14:28:38Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [x] TDD: `tests/test_new_wires_edges.py` adds a case asserting that after `goc new child --advances parent --commit` returns, `git status --porcelain` is clean for the parent card path (no ` M` on `<deck>/parent/README.md`) — `test_new_with_commit_flag_commits_both_endpoints_and_new_card`
  - [x] TDD: same test asserts the new card directory is tracked by the same commit (Option C with `--commit`); a sibling `test_new_default_does_not_commit` pins the default-leaves-it-untracked branch of the contract
  - [x] EMPIRICAL: reproduce.py exits zero (defect no longer fires) — verified by running it locally
  - [x] MECHANICAL: `goc new --help` lists `--commit` / `--no-commit`, matching the flag surface of `goc advance` / `goc unadvance` / `goc wait` / `goc decide`
  - [x] PROCESS: `Skill(create-card)` Step 4 examples and `Skill(advance-card)` "Verbs" reference now recommend `--commit` for wired filings, removing the implicit manual `git add` follow-up
worker: {who: "claude[bot]", where: main}
---

# goc-new-with-advances-leaves-parent-card-mutation-uncommitted

## Location

`goc/engine.py:4091-4156` — `_cmd_new`. The tail at lines 4151-4154
calls `_mutate_pair` to write both endpoints of each edge to disk but
returns without invoking `_git_auto_commit`. Argparse at
`goc/engine.py:2626-2646` confirms `p_new` has no `--commit` /
`--no-commit` flags.

## What's broken

The four other edge-mutating verbs (`advance`, `unadvance`, `wait`,
`decide`) all share the same shape: mutate via `_mutate_pair`, then
auto-commit both endpoints. The relevant tails:

```python
# goc/engine.py:4396-4401  (_cmd_advance)
_mutate_pair(title, advancer, "advanced_by", "advances", add=True)
print(f"advance: {title}.advanced_by += {advancer}; {advancer}.advances += {title}")
commit_policy = _commit_override(commit, no_commit)
if auto_commit_enabled(commit_policy):
    if _git_auto_commit([DECK_DIR / title, DECK_DIR / advancer], f"deck: {advancer} advances {title}"):
        print("  committed")
```

```python
# goc/engine.py:4410-4415  (_cmd_unadvance) — same shape
```

`_cmd_new` does the same disk mutation through `_mutate_pair` but
omits the commit step:

```python
# goc/engine.py:4151-4156  (_cmd_new tail)
for target in advances:
    _mutate_pair(target, title, "advanced_by", "advances", add=True)
for advancer in advanced_by:
    _mutate_pair(title, advancer, "advanced_by", "advances", add=True)
print(f"created {card_dir.relative_to(REPO_ROOT)}/")
print(f"Next: edit ... to fill the body and DoD; ...")
```

The predecessor card
[half-edge-errors-recur-because-goc-new-cannot-wire-edges](../half-edge-errors-recur-because-goc-new-cannot-wire-edges/)
added the `--advances` / `--advanced-by` flags so both file writes
land atomically on disk — and that invariant holds. The gap is one
level up: file-level atomicity without commit-level atomicity is not
enough when AGENTS.md's "Parallel-Agent Commit Safety" section
instructs agents to stage **only explicit file paths**:

> When it is your turn, stage only explicit file paths with
> `git add <path>...`. Do not use `git add .`, `git add -A`,
> directory-wide adds [...] to isolate your work.

An agent filing `goc new bug-X --advances epic-Y` and then committing
only `.game-of-cards/deck/bug-X/` ships a half-edge: `bug-X.advances`
is committed, but `epic-Y.advanced_by` lingers in the worktree as
ambient WIP indefinitely (or gets bundled into the next unrelated
commit if a later `git add -A` sweeps it up).

## Empirical evidence

`deck/<title>/reproduce.py` scaffolds a fresh repo, runs
`goc install`, then files a parent and a child wired with
`--advances`, and prints `git status --porcelain`:

```
?? .game-of-cards/deck/parent-card/        # after `goc new parent-card`, before commit
 M .game-of-cards/deck/parent-card/README.md   # after `goc new child-card --advances parent-card`
?? .game-of-cards/deck/child-card/
```

The ` M` line is the half-edge in flight: parent's `advanced_by` is
written but uncommitted.

## Why it matters

This is a wrong-by-default multi-agent-safety regression that
reintroduces the exact defect family the predecessor card
catalogued. Reachability path: every autonomous `pull-card` / `loop`
agent that files a sub-card via `Skill(create-card)` runs
`goc new ... --advances ...` — the Step 4 example in
`create-card/SKILL.md` recommends it as the preferred one-shot. So
every wired filing through that skill produces the ambient `M` on
the parent card. Whether it becomes a committed half-edge depends
entirely on the agent's subsequent staging choices; the framework
provides no guard.

Cross-references:

- [half-edge-errors-recur-because-goc-new-cannot-wire-edges](../half-edge-errors-recur-because-goc-new-cannot-wire-edges/) — the predecessor that delivered file-level atomicity for `goc new`'s edge writes. This card is the commit-level follow-on.
- [half-edge-repair-requires-manual-multi-file-edits](../half-edge-repair-requires-manual-multi-file-edits/) — the family `meta-fix` tag links this to.
- [repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string](../repair-edges-misses-half-edge-when-inverse-side-is-a-bare-string/) — the cleanup path that exists *because* half-edges keep being generated.

## Decision

*Resolved 2026-05-30T13:56:48Z:* Option C: add --commit/--no-commit flags to goc new (matching the sibling edge verbs' flag surface), default no-commit so today's scaffold-then-fill-in behavior is unchanged; create-card Step 4 recommends --commit for wired filings

*Reasoning:* preserves the zero-default-surprise scaffold workflow that is the point of goc new while giving agents an explicit opt-in to close the half-edge; the maintainer accepts that skill-body guidance is the enforcement surface for the common case

## Fix sketch (any option)

In `_cmd_new`, after the `_mutate_pair` loops, build the set of
paths to commit. For Option A: `[DECK_DIR / t for t in advances +
advanced_by]`. For Option B: prepend `card_dir`. For Option C:
gate the same block behind `auto_commit_enabled(commit_policy)`.
The argparse changes are a copy-paste of lines 2672-2675 from
`p_advance` into `p_new`.

Tests live in `tests/test_new_wires_edges.py` — add a `_cmd_new`-was-the-mutator
variant of the existing `git status` clean assertion. The closed
predecessor's test already asserts file-level edge symmetry; this
card extends to commit-level cleanliness.
