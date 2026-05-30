---
title: deck-auto-commit-sweeps-unrelated-staged-files-into-card-commits
summary: "`_git_auto_commit` stages and diff-checks with explicit pathspecs, then runs `git commit -m <msg>` with NO pathspec — so any unrelated file a parallel agent had staged is bundled into the deck commit. Violates AGENTS.md's Parallel-Agent Commit Safety contract verbatim. Reachable from every status-flip verb (`goc status`, `goc done`, `goc wait`, `goc advance`, `goc unadvance`, `goc decide`)."
status: open
stage: null
contribution: high
created: "2026-05-30T09:40:17Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero on a clean checkout (co-agent staged file is NOT in the resulting card commit).
  - [ ] TDD: a new regression test in `tests/` drives `_git_auto_commit` against a repo with an unrelated staged file and asserts the file is absent from `git show --name-only HEAD`.
  - [ ] MECHANICAL: `engine.py:3409` invokes `git commit` with an explicit pathspec (`["git", "commit", "-m", message, "--", *paths]`) so it can only commit the card paths it was given.
  - [ ] PROCESS: `uv run goc validate` is clean.
---

# Deck auto-commit sweeps unrelated staged files into card commits

## Location

- Defect: `goc/engine.py:3401-3409` (`_git_auto_commit`).
- Contract violated: `AGENTS.md:354-362` ("Parallel-Agent Commit Safety").

## What's broken

`_git_auto_commit` is the single funnel for the deck's auto-commit
policy — every status-flip verb routes through it (`goc status`,
`goc done`, `goc wait`, `goc advance`, `goc unadvance`, `goc decide`;
see callers at `engine.py:4026, 4387, 4408, 4422, 4614`). It accepts an
explicit `card_dirs` list, builds a pathspec from the card's
`README.md` / `log.md`, stages with that pathspec, and even checks
`git diff --cached --quiet --` against that pathspec — and then drops
the pathspec on the actual commit:

```python
# goc/engine.py:3393-3409
paths: list[str] = [
    str(p.relative_to(DECK_ROOT))
    for d in card_dirs
    for fname in ("README.md", "log.md")
    if (p := d / fname).exists()
]
if not paths:
    return False
subprocess.run(["git", "add", "--", *paths], check=True, cwd=git_cwd)
diff_check = subprocess.run(
    ["git", "diff", "--cached", "--quiet", "--", *paths],
    cwd=git_cwd,
    check=False,
)
if diff_check.returncode == 0:
    return False
subprocess.run(["git", "commit", "-m", message], check=True, cwd=git_cwd)
return True
```

The `diff_check` succeeds whenever the card paths have changes —
even if the index *also* contains unrelated files staged by a parallel
agent. The subsequent `git commit -m message` (no `--`, no pathspec)
then commits the entire index.

This contradicts the project's own contract, set verbatim in AGENTS.md:

```
When it is your turn, stage only explicit file paths with
`git add <path>...`. Do not use `git add .`, `git add -A`, directory-wide
adds, `git stash`, or destructive cleanup (`git restore`, `git checkout --`,
`git reset --hard`, `git clean`) to isolate your work; those operations can
move or discard another agent's WIP. Verify the staged set with
`git diff --cached --stat`, then commit with an explicit pathspec:
`git commit -- <path>...`. The pathspec is the last guard against
accidentally bundling unrelated staged files.
```

The deck's own auto-commit machinery violates "the last guard."

## Empirical evidence

`reproduce.py` constructs a temp git repo with a one-card deck, stages
an unrelated `stray-from-another-agent.txt` (simulating a co-agent's
WIP), mutates the card's README, and calls `_git_auto_commit` with
ONLY the card directory as its pathspec argument:

```
[main 056cfef] deck: fake-card open → active
 2 files changed, 2 insertions(+)
 create mode 100644 stray-from-another-agent.txt
Files in the auto-commit:
  .game-of-cards/deck/fake-card/README.md
  stray-from-another-agent.txt

AGENTS.md:359-360 requires `git commit -- <path>...`; engine.py:3409 omits the pathspec.
Co-agent WIP bundled into card commit? True
DEFECT REPRODUCED: unrelated staged file was swept into the card commit despite
_git_auto_commit being given only the card directory as its pathspec argument.
```

The card commit landed two files, even though only one was passed as a
pathspec. Exit code 1.

## Why it matters

Reachability path is direct. Every status-flip verb in the engine
funnels through `_git_auto_commit`, and the engine's whole reason for
existing is multi-agent operation against a shared `main` (the
`/loop pull-card 30m` and `/schedule pull-card weekday 09:00` patterns
documented in the `pull-card` skill explicitly anticipate concurrent
sessions). The defect's triggering condition — "another agent has
unrelated files in the index at commit time" — is exactly the
scenario the AGENTS.md contract was written to defend.

Concrete failure modes:

1. **Mixed-domain commits.** A `deck: foo open → active` commit picks
   up the user's WIP from an unrelated feature branch checkout. Reverting
   the deck flip later (`git revert`) reverts the WIP too.
2. **Quiet leakage of secrets / WIP.** If a co-agent had staged a
   credential file or a draft document, it now lives in the deck's
   committed history under a misleading subject line.
3. **Race-window enlargement.** AGENTS.md's preflight rule ("before
   staging, run `git diff --cached --name-only` … wait with short
   backoff") is meant to catch this, but it can't protect against an
   agent that stages between the preflight read and our commit. The
   pathspec on commit is the design's *last* defense; removing it
   collapses the safety story.

## Fix

One-line change at `engine.py:3409`:

```diff
-        subprocess.run(["git", "commit", "-m", message], check=True, cwd=git_cwd)
+        subprocess.run(["git", "commit", "-m", message, "--", *paths], check=True, cwd=git_cwd)
```

This re-uses the `paths` list already built two statements earlier —
no other change is needed. The pathspec restricts the commit to the
same set the add and diff checks already operate on, restoring the
"last guard" the AGENTS.md contract requires.

Add a regression test in `tests/` that drives `_git_auto_commit`
against a temp repo with an unrelated staged file and asserts the
file is absent from `git show --name-only HEAD`. The test in
`reproduce.py` can be adapted directly.

## Surfaced by

`audit-deck` round, 2026-05-30, `general-purpose` hunter candidate #1
of 3. Empirically reproduced above.
