---
title: publish-and-claim-commit-a-new-card-without-the-parent-edge-goc-new-wrote
summary: "goc new child --advances parent writes the parent's advanced_by on disk but, without --commit (the default), leaves it uncommitted. The verbs that release the new card, goc publish and the goc status active claim, auto-commit only the card's own directory, so HEAD gets child.advances naming a parent whose committed advanced_by lacks it, and a fresh clone fails goc validate with a half-edge. The documented default flow, scaffold then author then publish or claim, corrupts the committed deck with no manual staging step involved."
status: active
stage: null
contribution: high
created: "2026-11-16T01:20:11Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: a `reproduce.py` runs the Falsification recipe (`goc new` with `--advances` and with `--advanced-by`, then `goc publish`, and separately `goc status <title> active`) and prints whether HEAD validates on a fresh clone. Run it on today's engine, record the verdict in log.md, and drop the `unverified` tag once it works.
  - [ ] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix. After either release verb, `git status --porcelain` shows no uncommitted edge counterpart of the released card, and `goc validate` on a fresh clone of HEAD exits 0.
  - [ ] TDD: `tests/test_new_wires_edges.py` (or a sibling) pins both release verbs on a card filed with `--advances` and without `--commit`, and fails on today's engine.
  - [ ] MECHANICAL: the `_git_auto_commit` docstring (`goc/engine.py:5698-5699`) and `Skill(create-card)` Step 4 (`SKILL.md:130-132`) describe what the release commit contains, and plugin mirrors are re-synced (`python scripts/sync_plugin_assets.py --check` green).
worker: {who: "claude[bot]", where: main}
---

# Publishing or claiming a new card commits it without the parent edge `goc new` wrote

Parked as `unverified`. A hunter agent reproduced it during an audit-deck run,
and the auditing agent reproduced it again by hand (output below), but there
is no `reproduce.py` yet.

## Hypothesis

`goc new` writes the counterpart edge to the other card's README right away
(`goc/engine.py:7097-7098`):

```python
    for target in advances:
        _mutate_pair(target, title, "advanced_by", "advances", add=True)
```

It commits both endpoints only on an explicit `--commit` (`:7116`,
`if _commit_override(commit, no_commit) is True:`). The default leaves the
parent's README modified in the worktree. Two of `goc new --help`'s three
examples (`:4600-4601`) omit `--commit`.

The verbs that release the authored card then commit only its own directory:

- `goc publish` (`goc/engine.py:6925`):
  `if _git_auto_commit([card_dir], f"deck: publish {title}"):`
- the claim, `goc status <title> active` (`goc/engine.py:6872`):
  `commit_targets = [card_dir]` (plus a successor on supersede, nothing else)

So with `auto_commit: true`, the default, HEAD records `child.advances:
[parent]` while the parent's committed `advanced_by` lacks `child`. The
parent's half is left as an uncommitted ` M` for whoever commits next, if
anyone does.

Two docs say otherwise:

- `_git_auto_commit`'s docstring (`goc/engine.py:5698-5699`) names exactly
  these verbs as the ones that "legitimately commit a freshly-authored card".
- `Skill(create-card)` Step 4 (`SKILL.md:130-132`) warns that "an
  explicit-pathspec commit of just the new directory ships a half-edge".

Here goc's own release commit is that explicit-pathspec commit.

## Falsification recipe

Run on 2026-11-16 against `main` at `ada1d2e7`, in a scratch repo with
`.game-of-cards/deck/` and the default config (`auto_commit` on):

1. Commit an authored `parent-card`.
2. Run `goc new child-card --advances parent-card --summary child --gate none --tag bug`.
3. Replace the child's DoD and body placeholders.
4. Run `goc publish child-card`.
5. Run `git status --porcelain`, then `git show HEAD:<deck>/parent-card/README.md`.
6. Run `goc validate` on a fresh clone.

Observed:

```
--- goc publish child-card:
child-card: published (draft flag cleared); now visible in the queue
  committed
--- git status --porcelain:
 M .game-of-cards/deck/parent-card/README.md
--- HEAD parent advanced_by:
advanced_by: []
--- validate on a fresh clone of HEAD:
ERROR: child-card: advances contains 'parent-card' but parent-card.advanced_by is missing 'child-card' (half-edge)
Run 'goc repair-edges --apply' to fix.
validate exit=1
```

The hunter saw the same with `goc status child-card active` in place of
publish: the commit `deck: child-card open → active` left the parent
uncommitted, and validate on HEAD exited 1.

The hypothesis is falsified if, after either release verb, the parent's
counterpart edge is committed (or the verb refuses or warns) and HEAD
validates.

## Why it matters

- It needs no unusual input. `auto_commit: true` and `goc new` without
  `--commit` are both defaults, and claiming is the usual next step after
  filing.
- Every fresh clone, CI checkout or second worker fails `goc validate` until
  someone commits the stray parent edit. A worker that runs
  `goc repair-edges --apply` instead re-adds the edge but leaves it
  uncommitted too
  ([goc-repair-edges-apply-leaves-edge-repairs-uncommitted](../goc-repair-edges-apply-leaves-edge-repairs-uncommitted/)).
- A repo with a pre-commit `goc validate` hook would probably see the release
  auto-commit fail instead. That variant is not verified here.

Related cards, neither about this path:

- [goc-new-with-advances-leaves-parent-card-mutation-uncommitted](../goc-new-with-advances-leaves-parent-card-mutation-uncommitted/)
  (done) kept no-commit as `goc new`'s default and added `--commit`. Its
  premise was that a committed half-edge depends on the agent's later
  staging. This card shows goc's own release verbs make that staging choice.
- [auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft](../auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/)
  (open) shows the same symptom through a different path: there the draft
  filter drops the counterpart from the commit set.

## Why deferred

The audit round filed its own card and parked the hunter's other candidates;
there was no budget for a `reproduce.py`. The fix has more than one shape:

- Widen the release commit to the edge counterparts that are modified in the
  worktree and name the released card.
- Make `goc new --advances/--advanced-by` commit by default.
- Refuse or warn at release while a counterpart edge is uncommitted.

Surfaced by: the audit-deck hunter subagent (general-purpose, briefed on the
scheduler core: publish, claim, queue views).
