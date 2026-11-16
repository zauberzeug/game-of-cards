---
title: publish-and-claim-commit-a-new-card-without-the-parent-edge-goc-new-wrote
summary: "goc new child --advances parent writes the parent's advanced_by but, without --commit (the default), leaves it uncommitted, and the verbs that release the new card, goc publish and the goc status active claim, auto-committed only the card's own directory, so HEAD recorded a half-edge that failed goc validate on every fresh clone. Fixed in _git_auto_commit, which now also commits each edge counterpart whose worktree README holds the other half of an edge the commit records while its committed README lacks it. Only a tracked counterpart's README joins, one HEAD already agrees with stays out, and a draft counterpart is never added, which leaves that case to the open decision on auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft."
status: done
stage: null
contribution: high
created: "2026-11-16T01:20:11Z"
closed_at: "2026-11-16T05:03:06Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [x] EMPIRICAL: a `reproduce.py` runs the Falsification recipe (`goc new` with `--advances` and with `--advanced-by`, then `goc publish`, and separately `goc status <title> active`) and prints whether HEAD validates on a fresh clone. Run it on today's engine, record the verdict in log.md, and drop the `unverified` tag once it works. — on `89f16b7e` it printed `DEFECT: 4 of 4 release paths commit a half-edge` (exit 1); verdict in log.md, `unverified` dropped.
  - [x] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix. After either release verb, `git status --porcelain` shows no uncommitted edge counterpart of the released card, and `goc validate` on a fresh clone of HEAD exits 0. — all four paths print `uncommitted parent paths: none` and `validate on a fresh clone of HEAD: exit=0`; exit 0.
  - [x] TDD: `tests/test_new_wires_edges.py` (or a sibling) pins both release verbs on a card filed with `--advances` and without `--commit`, and fails on today's engine. — `test_release_verbs_commit_the_edge_half_goc_new_left_uncommitted` (both flags × both verbs) plus four neighbours; 7 subtest failures on `89f16b7e`, green after.
  - [x] MECHANICAL: the `_git_auto_commit` docstring (`goc/engine.py:5698-5699`) and `Skill(create-card)` Step 4 (`SKILL.md:130-132`) describe what the release commit contains, and plugin mirrors are re-synced (`python scripts/sync_plugin_assets.py --check` green). — docstring now at `goc/engine.py:5829-5838`, Step 4 at `SKILL.md:129-133`; `--check` and `port_skills_to_openclaw.py --check` both green.
worker: {who: "claude[bot]", where: main}
---

# Publishing or claiming a new card commits it without the parent edge `goc new` wrote

## What was broken

Verified on 2026-11-16 by `reproduce.py`, in all four combinations of the two
wiring flags and the two release verbs.

`goc new` writes the counterpart edge to the other card's README right away
(`goc/engine.py:7237-7240`) and commits only on an explicit `--commit`
(`:7256`, `if _commit_override(commit, no_commit) is True:`). The default
leaves the parent's README modified in the worktree, and two of
`goc new --help`'s three examples (`:4600-4601`) omit `--commit`.

The verbs that release the authored card then committed only its own
directory:

- `goc publish` (`goc/engine.py:7065`):
  `if _git_auto_commit([card_dir], f"deck: publish {title}"):`
- the claim, `goc status <title> active` (`:7012`):
  `commit_targets = [card_dir]` (plus a successor on supersede, nothing else)

So with `auto_commit: true`, the default, HEAD recorded `child.advances:
[parent]` while the parent's committed `advanced_by` lacked `child`, and the
parent's half sat as an uncommitted ` M` for whoever committed next. Two docs
said otherwise: `_git_auto_commit`'s docstring named these verbs as the ones
that "legitimately commit a freshly-authored card", and `Skill(create-card)`
Step 4 warned that "an explicit-pathspec commit of just the new directory
ships a half-edge". goc's own release commit was that explicit-pathspec
commit.

## Evidence

`reproduce.py` sets up a scratch repo per combination, with
`workflow.auto_commit: true` and git isolated from the host's global config.
It commits an authored `parent-card` and files `child-card` with
`--advances parent-card` or `--advanced-by parent-card` and no `--commit`.
Then it authors the child, releases it with `goc publish` or
`goc status child-card active`, and runs `goc validate` on a fresh clone of
HEAD. Exit 1 while any combination fires, 0 once none does.

Before the fix (`main` at `89f16b7e`), every combination fired. The first one:

```
=== goc new child-card --advances parent-card; goc publish child-card
  release output:   committed
  uncommitted parent paths: [' M .game-of-cards/deck/parent-card/README.md']
  validate on a fresh clone of HEAD: exit=1
    ERROR: child-card: advances contains 'parent-card' but parent-card.advanced_by is missing 'child-card' (half-edge)
    Run 'goc repair-edges --apply' to fix.
  verdict: DEFECT
...
DEFECT: 4 of 4 release paths commit a half-edge
```

After the fix:

```
=== goc new child-card --advances parent-card; goc publish child-card
  release output:   committed
  uncommitted parent paths: none
  validate on a fresh clone of HEAD: exit=0
  verdict: ok
...
OK: every release path commits the counterpart edge; HEAD validates
```

## Fix

`_git_auto_commit` (`goc/engine.py:5807`) now also commits every edge
counterpart that holds the uncommitted other half of an edge a committed card
records. `_uncommitted_edge_counterparts` (`:5729`) finds them. The rule lives
in the shared commit helper rather than in the two release verbs, so
`goc decide`, `goc wait` and every other auto-committing verb cannot put the
same half-edge in HEAD either.

- **Which counterparts.** A counterpart qualifies when its worktree README
  records the other half and its committed README does not.
  `_git_head_texts` (`:5686`) reads the committed copies in one
  `git cat-file --batch` round trip, not a `git show` per child.
- **Which files.** A tracked counterpart contributes only its README.md, where
  the edge lives, so its owner's uncommitted log.md stays out. A counterpart
  HEAD lacks altogether commits whole (README.md and log.md).
- **Transitively.** Each counterpart taken is checked the same way in turn.
  Git commits its README whole, so it would otherwise bring along its own
  edges to cards HEAD has not seen.
- **Precision.** A counterpart whose committed README already records the edge
  stays out, so unrelated edits to it are not swept into someone else's
  release.
- **Drafts.** A draft counterpart is never added. Whether a draft may join a
  commit for an edge's sake is the open decision on
  [auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft](../auto-commit-publishes-dangling-edges-when-counterpart-endpoint-is-a-draft/).
  That card's defect still fires unchanged.
- **Output.** The verb prints `also committed <title>: it holds the other half
  of an edge this commit records` ahead of its `committed` line.

The card listed three fix shapes. Widening the release commit is the one its
DoD requires: after either release verb, no counterpart may be left
uncommitted. Refusing or warning at release leaves the counterpart
uncommitted. Making `goc new --advances` commit by default reverses the
decision on
[goc-new-with-advances-leaves-parent-card-mutation-uncommitted](../goc-new-with-advances-leaves-parent-card-mutation-uncommitted/)
to keep scaffolding uncommitted, and would publish unauthored drafts.

Regression tests in `tests/test_new_wires_edges.py` (`:253-342`):

- both wiring flags × both release verbs;
- a tracked counterpart contributes only its README;
- the transitive case;
- a counterpart HEAD already agrees with stays out;
- a draft is never added.

On the pre-fix engine the first three fail (7 subtest failures). Planted
offenders show the last two can catch a regression: one fix ignores the
committed copy, the other admits drafts.

## Known limits

- **Whole-file commit.** If a counterpart's README lacks the edge in HEAD and
  also holds unrelated uncommitted edits, those edits ride along. Committing
  only the edge would need either a temporary index, which bypasses commit
  hooks, or a temporary rewrite of the counterpart's worktree file, which
  risks losing it.
- **Removals.** An edge removed from both worktree copies, then one endpoint
  committed alone, still leaves HEAD half-edged. No default flow produces that,
  because `goc unadvance` commits both endpoints.
- **Claim push.** With `claim_push: true`, a claim commit that now carries the
  parent's README can conflict on it during the push-retry rebase.
  `_git_claim_push_with_retry` reports any failed rebase as a claim race,
  which is
  [claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset](../claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset/).

## Why it matters

The defect needed no unusual input. `auto_commit: true` and `goc new`
without `--commit` are both defaults, and claiming is the usual next step
after filing. Every fresh clone, CI checkout or second worker failed
`goc validate` until someone committed the stray parent edit. A worker that
ran `goc repair-edges --apply` re-added the edge but left it uncommitted too
([goc-repair-edges-apply-leaves-edge-repairs-uncommitted](../goc-repair-edges-apply-leaves-edge-repairs-uncommitted/)).

Surfaced by: the audit-deck hunter subagent (general-purpose, briefed on the
scheduler core: publish, claim, queue views).
