---
title: claim-push-reports-success-when-rebase-drops-identical-racing-claim
summary: "`_git_claim_push_with_retry` only detects a claim race when the rebase *conflicts*. Two workers claiming the same card under the same worker identity produce patch-identical commits; the rebase deduplicates the loser's commit (exit 0), the push reports up-to-date, and the engine prints success — the second agent proceeds to work an already-claimed card. Same-identity fleets (multiple scheduled runners sharing one bot identity) are exactly the deployment claim_push targets."
status: open
stage: null
contribution: medium
created: "2026-06-12T05:40:59Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, infra, api-contract]
definition_of_done: |
  - [ ] PROCESS: post-rebase verification semantics chosen (Decision required below) and recorded in log.md.
  - [ ] TDD: reproduce.py exits zero inverted — the same-identity racing claim aborts (or warns and re-reads) instead of printing "pushed (after rebase)" with a vanished commit.
  - [ ] TDD: regression test covers both variants — patch-identical commit dropped by rebase, and byte-identical commit (same SHA, same-second timestamps) where the first push trivially succeeds.
  - [ ] TDD: a clean rebase that *keeps* the local commit (no race, remote moved for unrelated reasons) still pushes and reports success.
  - [ ] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green).
---

# claim_push reports success when the rebase drops an identical racing claim

The claim-race abort in `_git_claim_push_with_retry` fires only when `git
rebase origin/<branch>` exits nonzero. When the racing claims are
*patch-identical* — two workers claiming the same card with the same
worker identity, e.g. two scheduled runners both auto-populating `worker:
{who: claude[bot]}` — the rebase deduplicates the local commit via
patch-id and exits 0, the follow-up push reports "Everything up-to-date",
and the function prints `pushed (after rebase)` and returns True. The
loser's claim commit no longer exists, no abort fires, and the second
agent proceeds to work an already-claimed card — the precise double-work
race the claim protocol was designed to stop.

## Location

- `goc/engine.py:3999` — `if rebase.returncode != 0:` (the only race detection)
- `goc/engine.py:4035` — `print("  pushed (after rebase)"); return True` (no post-rebase check that the local claim commit survived)

## What's broken

```python
rebase = subprocess.run(["git", "rebase", f"origin/{branch}"], ...)
if rebase.returncode != 0:
    ... abort + "claim race — already claimed by {other!r}" ...
push2 = subprocess.run(["git", "push", "origin", branch], ...)
if push2.returncode == 0:
    print("  pushed (after rebase)")
    return True
```

The designed contract (closed card
[design-claim-protocol-with-branch-and-author-metadata](../design-claim-protocol-with-branch-and-author-metadata/))
is that a claim push "either propagates the claim or aborts naming the
racing worker". A patch-identical race does neither: the rebase silently
drops the local commit, nothing verifies it survived, and success is
reported. There is also a stronger sub-variant: when the two claims land
in the same second, the commits are *byte-identical* (same SHA), the
loser's first push trivially succeeds with "Everything up-to-date", and
the rebase path is never even reached.

The race detection is therefore identity-conditional: only a
*different*-identity claim conflicts in the rebase and triggers the abort.

## Empirical evidence

`uv run python .game-of-cards/deck/claim-push-reports-success-when-rebase-drops-identical-racing-claim/reproduce.py`:

```
[clone A claim, who=claude[bot]] exit=0
[clone B same-identity claim]    exit=0
  [main 330a924] deck: fix-the-widget open → active
  fix-the-widget: open → active
    committed
    pushed (after rebase)
  clone B unpushed commits after 'success': <none — claim commit vanished>
[clone C different-identity claim] exit=2
  ERROR: fix-the-widget: claim race — already claimed by 'claude[bot]' on origin/main. Your local claim commit is unpushed; reset to origin/main and pull a different card.

DEFECT CONFIRMED: a same-identity racing claim is reported as pushed while its commit was silently dropped; only a different-identity race triggers the designed abort.
```

## Why it matters

Reachability: any multi-runner setup sharing a worker tag
(`GOC_WORKER=claude[bot]`, this repo's own scheduled pull-card bots) with
`workflow.claim_push: true`. The open decision card
[parallel-agents-double-close-cards-because-claim-protections-are-disabled](../parallel-agents-double-close-cards-because-claim-protections-are-disabled/)
assumes enabling `claim_push` fixes the double-close incident; this hole
means the same-identity variant of that incident passes silently even
with the protection enabled — and same-identity fleets are the *expected*
configuration for autonomous bots, not an edge case. The two cards should
be decided together.

Family note: this is a third instance of the "verb reports success
without verifying its effect" shape documented by
[goc-advance-claims-success-when-adding-an-already-existing-edge](../goc-advance-claims-success-when-adding-an-already-existing-edge/)
and
[goc-unadvance-claims-success-when-removing-a-non-existent-edge](../goc-unadvance-claims-success-when-removing-a-non-existent-edge/)
(both `meta-fix`-tagged). A fourth instance should trigger the
architectural meta-fix card per the audit sibling-sweep rule.

## Decision required

What should a claim do when the post-rebase state shows its commit was
absorbed by a remote claim?

1. **Abort like a conflict** — after a clean rebase, check `git rev-list
   origin/<branch>..HEAD` is non-empty before declaring success; if
   empty, emit the same "claim race — already claimed by" error
   (identity read from the remote README) and exit nonzero. Treats
   same-identity races as races: the second runner pulls a different
   card. Simplest, symmetric with the existing abort.
2. **Adopt the remote claim** — if the remote claim's `worker.who`
   equals the local identity, report "already claimed by you (remote);
   proceeding" and return success. Avoids spurious aborts when a single
   human retries from two checkouts, but lets two same-identity *fleet*
   runners both proceed — exactly the double-work this protocol exists
   to prevent.
3. **Abort, with an explicit `--reclaim` escape hatch** — option 1 by
   default; a flag (or `worker.where` mismatch check) for the legitimate
   same-person-two-checkouts case.

Option 1 or 3; the question is whether the same-identity-retry UX matters
enough to warrant the extra surface. A human should pick.
