---
title: goc-new-with-advances-leaves-parent-card-mutation-uncommitted
summary: "`goc new <child> --advances <parent>` writes the parent's `advanced_by` edge to disk but never commits it, leaving the parent README as ambient `M` in the worktree. An agent that follows AGENTS.md's explicit-pathspec rule and commits only the new card directory ships a half-edge — exactly the integrity defect `goc repair-edges` exists to clean up."
status: open
stage: null
contribution: high
created: "2026-05-29T16:21:00Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, meta-fix]
definition_of_done: |
  - [ ] TDD: `tests/test_new_wires_edges.py` adds a case asserting that after `goc new child --advances parent` returns, `git status --porcelain` is clean for the parent card path (no ` M` on `<deck>/parent/README.md`)
  - [ ] TDD: same test asserts the new card directory is either tracked by the same commit OR explicitly left untracked, matching the chosen option below
  - [ ] EMPIRICAL: reproduce.py exits zero (defect no longer fires)
  - [ ] MECHANICAL: `goc new --help` lists `--commit` / `--no-commit` if the chosen option introduces them, matching the flag surface of `goc advance` / `goc unadvance` / `goc wait` / `goc decide`
  - [ ] PROCESS: `Skill(create-card)` Step 4 examples and `card-schema` "Coordinating cards" reference reflect the new commit semantics (no manual `git add` follow-up implied by the example flow)
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

## Decision required

Three credible options:

### Option A — auto-commit only the parent-edge mutations when `--advances` / `--advanced-by` is used

Leave the new card itself untracked (preserving today's behavior of
"scaffold for editing"), but auto-commit the parent README updates
under a `deck: <child> advances <parent>` message — mirroring the
existing `advance` / `unadvance` commit messages.

- Pros: minimal behavior change. The user's typical "scaffold, fill
  in body, commit" loop is untouched. Half-edge gap closed.
- Cons: asymmetric — `goc new` commits something only sometimes.
  Two commits in the agent flow when the agent later commits the
  new card itself (one autocommit for the parent edge, one explicit
  commit for the child body).

### Option B — auto-commit everything: the new card directory AND any parent-edge mutations, in one commit

Mirror `goc advance` exactly. After `goc new child --advances parent`,
the worktree is clean.

- Pros: symmetric with the four sibling edge-mutating verbs.
  Single commit per `goc new` invocation. The agent's job
  simplifies to "fill in the README, then `goc done` or
  `goc advance ...`-driven follow-up".
- Cons: significant default-behavior change. Today users expect
  `goc new` to scaffold a card they then fill in and commit
  themselves; auto-committing an empty-body card creates noise in
  `git log` and a "fix up the placeholder DoD" follow-up commit
  per card.

### Option C — add `--commit` / `--no-commit` flags with default `no-commit`, leave today's behavior unchanged

Match the flag surface of the four sibling verbs but keep the
current "user commits explicitly" default. Agents opt in via
`goc new --commit ...`; `Skill(create-card)` Step 4 recommends
`--commit` for wired filings.

- Pros: zero default-behavior surprise. Maximum control. Cheapest
  to land.
- Cons: still wrong-by-default for the common case (an agent
  forgets the flag and ships a half-edge anyway). Skill-body
  guidance becomes the only enforcement, which AGENTS.md's
  predecessor history shows is not sufficient — guidance drift is
  why this family of bugs recurs.

The implementer should pick one; the DoD already encodes the
neutral set of asserts (status clean for the parent path; new card
directory tracked OR explicitly untracked, matching the chosen
option).

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
