---
title: dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting
status: open
stage: null
contribution: medium
created: "2026-06-18T05:14:50Z"
closed_at: null
human_gate: decision
advances: []
advanced_by:
  - goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run
  - migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees
  - dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir
  - repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses
tags: [meta-fix, infra, api-contract]
summary: |
  `goc install/upgrade/migrate --dry-run` maintains a hand-written preview
  (`_plan_writes` / migrate's preview branch) that re-enumerates conditionals
  the real executor applies independently. The two code paths drift: every
  time an executor grows a guard, the plan must be patched to match by hand,
  and when it isn't, the dry-run lies. Four instances have surfaced (three
  fixed one-by-one, one open in `repair-edges`); this card proposes one
  architectural fix so the plan derives from the executor instead of
  re-listing its decisions.
definition_of_done: |
  - [ ] PROCESS: decision recorded (see `## Decision required`) — pick the unification mechanism (plan-derived-from-executor, shared predicate table, or property-test that asserts plan/executor parity over a matrix of environments)
  - [ ] TDD: a single parity harness asserts dry-run plan == real executor effects across the environment matrix (git/non-git, identical-only migrate tree, hook-present/absent), failing if any future executor guard is not mirrored in the plan
  - [ ] MECHANICAL: the three already-fixed instances are folded into the harness as matrix rows (not separate bespoke tests)
  - [ ] PROCESS: each existing instance card gets a forward pointer to this root card
---

# dry-run-plan-reenumerates-executor-conditionals-and-keeps-drifting

## What keeps recurring

`goc`'s `--dry-run` preview is computed by a code path *separate* from the
one that performs the real work. The preview (`_plan_writes` in
`goc/install.py`, and the analogous preview branch in `migrate`) hand-lists
the writes it believes the executor will perform. But the executor makes its
own independent decisions — `_append_precommit_hook` guards on `.git`,
`migrate` unconditionally `rmtree`s the legacy tree, the upgrade path appends
the pre-commit hook only after `git init`. Every conditional the executor
grows must be *re-enumerated by hand* in the plan. When it isn't, the dry-run
promises a write the real run skips, or hides one the real run performs —
either way `--dry-run` stops being a truthful preview, which is its entire
contract.

## The instances so far

Four separate cards. The first three were each fixed by patching the plan to
re-mirror one executor conditional; the fourth (open) shows the same shape in
a different verb:

1. [goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run](../goc-upgrade-omits-pre-commit-hook-append-promised-by-dry-run/)
   — git-repo case: dry-run promised the pre-commit append, real upgrade
   omitted it. Fixed by making the executor perform it (commit bb01fcc).
2. [migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees](../migrate-dry-run-omits-legacy-tree-removal-for-identical-only-trees/)
   — migrate: dry-run hid the `Would remove legacy tree` line when every
   legacy card was identical, though the real run always `rmtree`s.
3. [dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir](../dry-run-plan-promises-pre-commit-append-that-real-install-skips-in-non-git-dir/)
   — non-git case: dry-run plan promised the pre-commit append, real install
   skipped it. Fixed by gating the plan line on `.git` (this card's trigger).
4. [repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses](../repair-edges-dry-run-overstates-fixable-edges-that-apply-refuses/)
   — `repair-edges`: the dry-run classifies half-edges against one original
   snapshot while `--apply` reloads before each edge, so the preview promises
   repairs apply then refuses as cycle-creating. The first instance outside
   the `install`/`upgrade`/`migrate` cluster — the drift is a `repair-edges`
   verb, not a `_plan_writes` write-plan — which widens the case that the
   architectural fix should be general rather than per-verb. Open (unfixed).

Instances 1 and 3 are the *same conditional* (`.git` presence around the
pre-commit append) drifting in opposite directions across two code paths —
the clearest signal that hand-mirroring is the root cause, not any single
guard. This is the same shape as the repo's other "X reimplements Y and keeps
drifting" meta-fix family
([yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting](../yaml-lite-quote-scanners-reimplement-the-same-state-machine-and-keep-drifting/),
[frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting](../frontmatter-emitter-quote-trigger-reenumerates-parser-shapes-and-keeps-drifting/),
[openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting](../openclaw-hook-predicates-reimplement-engine-logic-and-keep-drifting/)):
two code paths encode the same decision and drift because nothing forces them
to agree.

## Why it matters

`--dry-run` is documented as a truthful preview of what the real run will do.
Anyone evaluating GoC by previewing before committing — exactly the
risk-averse user the flag exists for — is the one who gets the wrong answer.
And the cost compounds: each new executor guard is a latent dry-run bug until
someone notices the plan didn't follow, and the fix-per-instance cadence
means the deck keeps absorbing these one at a time forever.

## Decision required

The instances are fixed; what's undecided is *how* to stop them recurring.
Three credible mechanisms, each with a different cost/coverage trade-off:

- **A — Plan derives from a dry-run executor pass.** Refactor the executor so
  it can run in a "record intended writes, perform none" mode, and have
  `--dry-run` print exactly those recorded intents. One code path, zero
  drift by construction. Highest correctness, highest refactor cost (the
  executor's side effects must be cleanly separable from its decisions).
- **B — Shared predicate table.** Extract each conditional (`.git` present?
  legacy tree non-empty?) into a single named predicate consumed by both the
  plan and the executor. Cheaper than A; drift is possible only if a new
  guard is added without routing through the table.
- **C — Parity property-test only.** Leave the two code paths as-is but add a
  regression harness that, over a matrix of environments (git/non-git,
  identical-only migrate tree, hook present/absent), asserts the dry-run plan
  matches the real run's actual effects. Cheapest; catches drift at CI time
  rather than preventing it by construction. The three per-instance tests
  fold into matrix rows.

A and C are not exclusive — C is the safety net regardless, and could ship
first while A/B is evaluated. The decision is which to commit to as the
primary mechanism (and whether C alone is judged sufficient given the
executor-refactor cost of A).

## Fix

Deferred to the recorded decision. Whichever mechanism is chosen, the DoD's
parity harness (folding the three existing instances into matrix rows) is the
common deliverable.
