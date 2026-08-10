## 2026-08-10 — the "may bundle" prediction is refuted; the real failure is a stranded deletion

An audit pass measured what the next auto-committing verb actually does
after `goc move`, and the answer is the opposite of what this card
predicted. The rewrites are never bundled into an unrelated card's
commit: every commit the engine makes is pathspec-scoped
(`git commit -m msg -- <paths>`), which bypasses the index for anything
outside the pathspec — the same property AGENTS.md § "Parallel-Agent
Commit Safety" relies on. So the deletion `git mv` staged is stranded
in the index instead, and the follow-up commit publishes the new card
directory while the old one stays in HEAD. Anyone who clones or pulls
gets two copies of the card, both of which `goc validate` reports OK.

The Option A fix sketch on this card was checked against that finding
and does not close it: `_git_auto_commit` builds its pathspec with an
`.exists()` filter (`engine.py:4677-4682`), so a deleted path can never
enter it no matter which directories are passed in.

Both corrections are applied to the README in place. The measurement,
the clone-side consequence, and the removal-handling decision it forces
are split out into
[card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck](../card-rename-leaves-a-duplicate-of-the-old-card-in-the-shared-deck/),
wired as `advanced_by` — this card's commit contract cannot be
correctly specified until that one picks how a removal reaches a
commit.
