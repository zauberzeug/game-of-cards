---
title: card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck
summary: "`goc move OLD NEW` stages the source-side deletion with `git mv` and never commits it. Every commit the engine and this repo's own agent rules make is pathspec-scoped, and `_git_auto_commit` builds its pathspec from paths that still exist on disk — so a deletion can never enter it. The next auto-committing verb publishes the new card directory while the old one stays in HEAD, and everyone who clones or pulls gets two copies of the same card, both of which `goc validate` reports OK."
status: open
stage: null
contribution: high
created: "2026-08-10T05:12:53Z"
closed_at: null
human_gate: decision
advances:
  - goc-move-leaves-cross-reference-rewrites-uncommitted
advanced_by:
  - deck-auto-commit-ignores-card-files-other-than-readme-and-log
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — after `goc move OLD NEW` plus any auto-committing verb, `git ls-tree -r HEAD` names the new card directory and NOT the old one, a fresh clone holds exactly one card directory, and the Option-A-shaped `_git_auto_commit` call no longer strands the deletion.
  - [ ] PROCESS: decide how a deck-file REMOVAL reaches a commit at all (the three options below), and record the reasoning in log.md. This is the decision the sibling card's Option A cannot make for us.
  - [ ] TDD: regression test in `tests/` asserts the post-rename HEAD tree contains only the new card directory — covering both the `git mv` path and the `shutil.move` fallback path (untracked source), since only the former stages a deletion.
  - [ ] TDD: regression test asserts `_git_auto_commit` (or its replacement) commits a card directory whose files were deleted on disk, so the fix holds for any future removal-shaped mutation and not just `move`.
  - [ ] MECHANICAL: the sibling card `goc-move-leaves-cross-reference-rewrites-uncommitted` has its "may silently bundle the move's rewrites into its commit" claim and its Option A fix sketch corrected in place (both are refuted by this card's evidence); `uv run goc validate` clean; plugin mirrors synced; pre-commit clean.
---

# Renaming a card leaves a duplicate of the old card in the shared deck

## Location

- `goc/engine.py:6270-6273` — `_cmd_move` renames the directory with
  `git mv`, which **stages** both halves of the rename: the addition of
  the destination and the *deletion* of the source.
- `goc/engine.py:6644` — `_cmd_move` returns after printing
  `old → new`. It never commits, so that staged deletion is left sitting
  in the index (the sibling card
  [goc-move-leaves-cross-reference-rewrites-uncommitted](../goc-move-leaves-cross-reference-rewrites-uncommitted/)
  covers the missing commit itself).
- `goc/engine.py:4677-4682` — `_git_auto_commit` builds its pathspec by
  filtering on existence, so a path that was deleted on disk can never
  appear in it:

  ```python
  paths: list[str] = [
      str(p.relative_to(DECK_ROOT))
      for d in card_dirs
      for fname in ("README.md", "log.md")
      if (p := d / fname).exists()
  ]
  ```

- `goc/engine.py:4685-4693` — and the commit it then makes is
  pathspec-scoped (`git add -- *paths`, `git commit -m message --
  *paths`), which by definition takes only those paths and leaves the
  rest of the index untouched.

## What's broken

The two facts compose into silent corruption of the shared deck.

`git mv` stages a deletion. `_git_auto_commit` structurally cannot
commit one. So the *next* auto-committing verb — `goc status`,
`goc decide`, `goc advance`, `goc done`, any of them — writes a commit
that adds the new card directory and says nothing about the old one.
The old directory stays in `HEAD` exactly as it was, while the index
holds a `D` entry that no goc verb will ever pick up.

The worktree that ran the rename looks correct: only the new directory
is on disk, and `goc` shows one card. The damage is only visible from
`HEAD` — that is, to everybody else.

This also refutes the mitigation the sibling card assumes. That card
predicts:

> A parallel agent's next auto-committing verb (e.g. `goc advance` on
> an unrelated card) may silently bundle the move's rewrites into its
> commit

It cannot. A pathspec commit bypasses the index for everything outside
the pathspec — that is what makes AGENTS.md § "Parallel-Agent Commit
Safety" prescribe `git commit -- <path>...` in the first place. The
staged deletion is not swept up; it is *stranded*, which is worse: a
swept-up deletion at least lands in some commit.

And the sibling card's proposed fix does not close this either. Its
Option A sketch is `_git_auto_commit([dst, *rewrite_dirs], ...)` —
`dst` and the cross-reference dirs, never `src`. `src` no longer
exists, so even naming it would not help: the `.exists()` filter drops
it. Part 3 of `reproduce.py` runs that exact call and the ghost still
lands in HEAD.

## Empirical evidence

`uv run python .game-of-cards/deck/card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck/reproduce.py`
(exit 1 = defect reproduces; exit 0 once fixed):

```
PART 1 — goc move + the next auto-committing verb
HEAD before move: ['.game-of-cards/deck/original-card-title/README.md']

`goc move original-card-title better-card-title` ran.
index after move (git diff --cached --name-status):
  R100	.game-of-cards/deck/original-card-title/README.md	.game-of-cards/deck/better-card-title/README.md
  R100	.game-of-cards/deck/original-card-title/log.md	.game-of-cards/deck/better-card-title/log.md

`goc status better-card-title active` ran (auto-commits).
HEAD after: ['.game-of-cards/deck/better-card-title/README.md', '.game-of-cards/deck/original-card-title/README.md']
index residue (never committed):
  D	.game-of-cards/deck/original-card-title/README.md
  D	.game-of-cards/deck/original-card-title/log.md

  ghost old card in HEAD:  True
  renamed card in HEAD:    True

PART 2 — what a teammate who clones actually gets
card directories in the clone: ['better-card-title', 'original-card-title']

`goc validate` in the clone:
  OK  better-card-title
  OK  original-card-title

`goc` (the pullable queue) in the clone:
  TITLE                STATUS  CONTR.  VALUE  GATE      TAGS  DOD
  -------------------  ------  ------  -----  --------  ----  ---
  original-card-title  open    medium    3.0  decision        0/1

  both copies present in the clone: True
  renamed-away card offered as pullable work: True
  goc validate exit code: 0 (0 = reports the deck clean)

PART 3 — the sibling card's Option A fix sketch, applied verbatim
committed: True
HEAD after the Option-A-style commit: ['.game-of-cards/deck/better-card-title/README.md', '.game-of-cards/deck/original-card-title/README.md']

  ghost STILL in HEAD after the sketched fix: True
```

## Why it matters

A rename is supposed to be a rename. What lands in the shared repo is
a **copy**, and every downstream reader is wrong in a different way:

- **The queue hands out work twice.** In the clone above,
  `original-card-title` is `status: open` and shows up as pullable. A
  second agent claims the card that was renamed away and redoes work
  that is already claimed under the new title. This is exactly the
  dedup/supersede race the `draft` flag was introduced to prevent, now
  reachable through a verb that is supposed to be a tidy-up.
- **`goc validate` cannot see it.** Both directories are internally
  well-formed, so validate reports `OK` for both and exits 0. The
  deck's own integrity check is blind to the one failure mode that
  duplicates a card, so nothing in CI catches it either.
- **The rename's cross-reference rewrites now point at the wrong
  card.** `_move_rewrite_tracked_files` rewrote every `advances` /
  `advanced_by` reference to the new slug, but the ghost still carries
  the old slug in its own frontmatter and edges. On a deck with real
  edges the clone gets dangling and asymmetric edges on top of the
  duplicate.
- **The operator has no signal.** The worktree is clean-looking, the
  verb printed `old → new`, and the follow-up verb printed
  `committed`. Discovering the ghost requires reading `git ls-tree
  HEAD` or waiting for a teammate to pull.

`goc move` is reachable from three ordinary paths, all of them
routine: a human tidying a title, the `Skill(refine-deck)` retitle
suggestion, and migration tooling under `--allow-jargon`.

## Reachability

The producer is `_cmd_move` itself; no upstream hands it pre-mutated
state. Reachability is direct and unconditional on the `git mv` path —
that is, whenever the card being renamed is already tracked, which is
every card that has been committed once. The `shutil.move` fallback
(untracked source, covered by
[goc-move-leaves-title-stale-on-uncommitted-cards](../goc-move-leaves-title-stale-on-uncommitted-cards/))
does not stage anything and so does not produce the ghost — a fix must
cover both paths without assuming either.

Confirmed on 2026-08-10 against this repo's engine at `50da03d1`.

## Decision required

The narrow question — "should `goc move` commit?" — belongs to the
sibling card. The question **this** card raises is one that card cannot
answer with either of its options, because both leave `_git_auto_commit`
unable to represent a removal:

> How does the deletion of a deck file reach a commit at all?

Three credible answers.

**Option 1 — teach `_git_auto_commit` to carry removals.** Replace the
`.exists()`-filtered file pathspec (`engine.py:4677-4682`) with
*directory* pathspecs, so deletions inside a card directory are
committed alongside its writes. Measured on git 2.54: `git add --
<dir>` + `git commit -- <dir>` carries a deletion inside `<dir>`, while
a pathspec naming only the surviving files leaves the removed path in
HEAD — the switch from file paths to the directory is the whole fix, no
`git add -A` needed. Smallest change, and it covers any future
removal-shaped mutation rather than just `move`. Cost: the pathspec
widens from two named files to a whole directory, which also sweeps in
sibling files an operator may not have meant to commit yet — precisely
the trade-off already being decided on
[deck-auto-commit-ignores-card-files-other-than-readme-and-log](../deck-auto-commit-ignores-card-files-other-than-readme-and-log/),
this card's `advanced_by` prerequisite. Its Options A and C are
directory pathspecs and fix this card for free; its Option B (extension
allowlist) does not.

**Option 2 — give `move` its own commit that names both endpoints.**
Leave `_git_auto_commit` alone and have `_cmd_move` commit the rename
itself with an explicit two-sided pathspec (`git commit -- <src>
<dst> <rewrite_dirs>`), which git accepts for a path that exists only
in HEAD. Keeps the general auto-commit helper narrow. Cost: a second
commit implementation in the engine, and it only fixes `move` — the
next verb that removes a file re-opens this card.

**Option 3 — refuse to leave the index dirty.** If the project prefers
`move` to stay stage-only (the sibling card's Option B), then
`_cmd_move` must at minimum leave a state that a pathspec commit
cannot corrupt: stage the rewrites too, and print an explicit
`Run \`git commit\` to finalize this rename — until you do, other goc
verbs will publish the new card without removing the old one.` Cheapest
and most honest about the shared-index hazard, but it leaves a footgun
armed for any operator who runs another goc verb first.

Whichever option wins, the sibling card's Option A sketch must be
amended — as written it ships the ghost.

## Fix sketch (under Option 1)

`goc/engine.py:4677-4682`, replacing the file-level pathspec with a
card-directory pathspec so removals are representable:

```python
paths: list[str] = [
    str(d.relative_to(DECK_ROOT))
    for d in card_dirs
    if d.exists() or _has_tracked_content(d)
]
...
subprocess.run(["git", "add", "--", *paths], check=True, cwd=git_cwd)
```

with `_cmd_move` then passing `[src, dst, *rewrite_dirs]` so the
source directory's removal is inside the pathspec. `src` no longer
exists on disk, which is precisely why the existence filter has to be
replaced by a tracked-content test rather than simply dropped.
