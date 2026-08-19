---
title: claim-push-calls-any-failed-rebase-a-claim-race-and-advises-a-reset
summary: "With `workflow.claim_push: true`, `_git_claim_push_with_retry` treats every non-zero `git rebase` exit as proof that another worker claimed the card, so an unrelated dirty working tree — or a rebase conflict in an unrelated file — is reported as `claim race — already claimed by <name>` with exit 2. The named rival is read from a `worker` field that survives release, so the message can name someone whose copy of the card on the remote is still `status: open`, and the prescribed remedy (reset to origin/<branch>) is the destructive cleanup AGENTS.md forbids. The neighbouring `closure_on_integration` check in the same file already separates a semantic git answer from a git error; the claim-push rebase branch is the same shape, never swept."
status: open
stage: null
contribution: medium
created: "2026-08-19T04:37:57Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, infra]
definition_of_done: |
  - [ ] PROCESS: mechanism chosen from the three options in "## Decision required" and recorded in this body + log.md. A race claim is only sound if it is derived from the remote card's own state, so the decision must say what evidence licenses the "already claimed by X" wording.
  - [ ] TDD: reproduce.py exits zero — neither an unrelated unstaged file nor an unrelated-file rebase conflict is reported as a claim race, and the clean-tree control still pushes after rebase.
  - [ ] TDD: regression test in `tests/` covers the claim_push retry path, which today has none: the three reproduce.py scenarios plus a genuine race (remote card `status: active` under a different `worker.who`) that MUST still abort.
  - [ ] MECHANICAL: `_git_claim_push_with_retry` (`goc/engine.py:5202`) no longer asserts a claim race from a bare `rebase.returncode != 0`, and never names a worker read off a card whose remote status is not `active`.
  - [ ] MECHANICAL: the remedy sentence at `goc/engine.py:5224` stops prescribing `reset to origin/<branch>` unconditionally — AGENTS.md "Parallel-Agent Commit Safety" forbids that cleanup class on a shared branch.
  - [ ] MECHANICAL: the `_git_claim_push_with_retry` docstring (`goc/engine.py:5146`) drops the premise "the rebase fails — meaning another worker modified the same card concurrently", which is the false inference this card is about.
  - [ ] MECHANICAL: exit-code contract for the non-race failure decided and documented — `pull-card` runs `goc status <title> active` and treats exit 2 as an aborted claim, so a warn-and-continue posture changes autonomous-loop behaviour.
  - [ ] MECHANICAL: plugin mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green).
---

# Claim push calls any failed rebase a claim race and advises a reset

## Summary

With `workflow.claim_push: true`, `goc status <title> active` pushes the
claim commit and retries once on non-fast-forward by rebasing onto the
remote. `_git_claim_push_with_retry` then treats **every** non-zero
`git rebase` exit as proof that another worker claimed the card. Two
routine, entirely unrelated conditions produce that exit — a dirty working
tree, and a rebase conflict in a file that has nothing to do with the card
— and both are reported as `claim race — already claimed by <name>`,
exit 2. The rival's name is read from a `worker` field that survives
release, and the prescribed remedy is a branch reset.

## Location

- `_git_claim_push_with_retry` — `goc/engine.py:5146` (the function)
- the collapsing branch — `goc/engine.py:5202` (`if rebase.returncode != 0:`)
- the message and its remedy — `goc/engine.py:5224`
- the rival-identity read — `goc/engine.py:5216` (`worker = fm.get("worker")`)
- the caller that turns the verdict into `sys.exit(2)` — `goc/engine.py:5871`
- the opt-in — `claim_push_enabled`, `goc/engine.py:5131`

## What's broken

The retry path rebases the local branch onto the remote and reads a single
bit — did rebase exit non-zero — as the answer to a question rebase was
never asked:

```python
rebase = subprocess.run(
    ["git", "rebase", f"origin/{branch}"], ...
)
if rebase.returncode != 0:
    subprocess.run(["git", "rebase", "--abort"], ...)
    other = "<unknown>"
    ...
    print(
        f"ERROR: {title}: claim race — already claimed by {other!r} on origin/{branch}."
        f" Your local claim commit is unpushed; reset to origin/{branch} and pull a different card.",
        file=sys.stderr,
    )
    return False
```

The function's own docstring states the inference as fact:

> Conflict semantics (per the design-claim-protocol decision): re-fetch and
> rebase on top of the remote. **If the rebase fails — meaning another worker
> modified the same card concurrently** — abort cleanly with the racing
> worker's identity so the caller knows the claim did not stick.

`git rebase` fails for reasons that have nothing to do with the card:

1. **A dirty working tree.** `git rebase` refuses outright — *"error: cannot
   rebase: You have unstaged changes."* It never looks at a single commit,
   let alone the card. `_git_auto_commit` stages an explicit pathspec of the
   card files only, so any other edit in the tree survives into this call,
   and AGENTS.md "Parallel-Agent Commit Safety" describes that as the normal
   state of a shared branch: *"Multiple agents may work on local `main` at
   the same time."*
2. **A conflict in an unrelated file.** `git rebase origin/<branch>` replays
   the whole local branch, not the claim commit. Any unpushed local commit
   that collides with the remote conflicts, and the card is never involved.

Three further problems compound the misdiagnosis:

- **The named rival is read off a field that outlives the claim.** The
  identity comes from `worker` on the remote card, but AGENTS.md documents
  that field as historical: *"The field persists after close as a historical
  record."* A card that was claimed and then released still carries the
  previous claimant. The engine never checks the remote card's `status`, so
  it will name a specific person as holding a card that reads `status: open`
  on the remote. The `<unknown>` fallback — printed whenever the field is
  simply absent — is the same message asserting a race it cannot attribute.
- **The prescribed remedy is the destructive cleanup this repo forbids.**
  "reset to origin/<branch>" is exactly what AGENTS.md "Parallel-Agent
  Commit Safety" rules out: *"Do not use `git add .`, `git add -A`,
  `git stash`, or destructive cleanup (`git restore`, `git checkout --`,
  `git reset --hard`, `git clean`) to isolate your work; those operations can
  move or discard another agent's WIP."* In case 1 the working tree holds
  uncommitted work, so following the advice destroys it — and the advice is
  given precisely because that work was there.
- **The claim already landed.** The caller exits 2 *after* the status flip and
  the local commit, so the card reads `status: active` with the current worker
  while the operator is told the claim "did not stick".

### The same shape, already fixed 50 lines away

[closure-on-integration-check-conflates-git-error-with-not-integrated](../closure-on-integration-check-conflates-git-error-with-not-integrated/)
(closed 2026-06-24) is this defect in `_enforce_closure_on_integration_or_exit`
— the *other* multi-worker opt-in in the same config block, in the same file.
Its fix separated the semantic answer from tool failure, and that function now
reads:

```python
if check.returncode == 1:          # goc/engine.py:5113 — genuinely not integrated
    ...
    sys.exit(2)
if check.returncode != 0:          # goc/engine.py:5121 — git error
    print("  Warning: ... could not determine reachability (git error); skipping check", ...)
    return
```

`_git_claim_push_with_retry` even splits its **fetch** failure correctly
(`goc/engine.py:5188` reports the real git output) and then collapses the
rebase one. The sibling sweep that would have caught this was never run; the
two functions sit 45 lines apart.

## Empirical evidence

`reproduce.py` builds a throwaway bare origin per case, so the cases cannot
contaminate one another. Verbatim output on this commit:

```
PASS  control: clean tree + divergent origin -> claim pushed after rebase
FAIL  BUG: an unrelated unstaged file is reported as a claim race (exit=2)
      ERROR: claim-race-probe: claim race — already claimed by '<unknown>' on origin/main. Your local claim commit is unpushed; reset to origin/main and pull a different card.
FAIL  BUG: an unrelated-file rebase conflict is reported as a claim race (exit=2)
      ERROR: claim-race-probe: claim race — already claimed by 'worker-three' on origin/main. Your local claim commit is unpushed; reset to origin/main and pull a different card.
      ...but the remote card is `status: open` — nobody holds it

2 failure(s)
```

The control case is the discriminator: with the identical divergent origin and
a **clean** tree, the retry works exactly as designed and prints
`pushed (after rebase)` with exit 0. Nothing about the card, the remote, or the
divergence differs between the control and case 2 — only the unrelated
unstaged file.

Case 3's last line is the attribution failure on its own: the remote card reads
`status: open`, and `worker-three` is a released claimant the field kept.

## Why it matters

`claim_push` is off by default, which bounds the blast radius — but the config
comment scopes it to exactly the deployment where these conditions are routine:

> `claim_push: true` — uncomment for multi-human / multi-agent setups.

In that deployment the failure is not a cosmetic message. An operator (or an
unattended runner) is told a named colleague holds the card and is instructed
to reset the branch. Doing so discards the very working-tree changes that
caused the error. Declining to reset leaves a card that is locally `active` and
committed while the command reported failure with exit 2 — so the two workers'
views of who holds the card now genuinely diverge, which is the state
`claim_push` exists to prevent.

The reachability path is short and does not require a race: any agent running
`goc status <title> active` on a shared branch with in-progress edits, at a
moment when the remote has moved, reaches it.

## Decision required

The precedent card's fix was a pure exit-code discrimination because
`git merge-base --is-ancestor` defines three codes. `git rebase` does not — it
exits 1 for both "conflict" and "cannot rebase: you have unstaged changes" — and
case 3 shows that even a *genuine* rebase conflict is not evidence of a claim
race. So the mechanism is a real choice:

**Option A — pre-flight precondition.** Before committing the claim, refuse when
the working tree is dirty (`git status --porcelain` non-empty), with a message
naming the actual blocker. Cheap and honest, but it makes a dirty tree block
claiming outright — a behaviour change on the happy path for every `claim_push`
user, and unattended runners commonly carry WIP.

**Option B — derive the race from the card, not from git's exit code.** After
any rebase failure, read the remote card and assert a race only when it is
`status: active` under a different `worker.who`. Otherwise report the real git
error. This is the only option whose "already claimed by X" is actually
entailed by evidence, and it also repairs the `<unknown>` case. Costs one extra
`git show` on the failure path, and needs a rule for a `worker`-less active card.

**Option C — mirror the precedent literally.** Distinguish "rebase never
started" (dirty tree) from "rebase conflicted" by stderr or by probing for a
paused rebase, warn-and-skip on the former, keep the race error for the latter.
Closest to the closed card, but it still calls case 3 — an unrelated-file
conflict — a claim race, so it fixes one of the two reproduced symptoms.

Coupled sub-question, whichever option wins: **the exit code.** Today any
`False` return becomes `sys.exit(2)` (`goc/engine.py:5871`). `pull-card` runs
`goc status <title> active` to claim, so exit 2 aborts the pull. If a non-race
failure warns instead of aborting, the claim stands locally but unpublished —
which is what the detached-HEAD branch (`goc/engine.py:5182`) already does,
except that it too returns `False` and therefore exits 2 after printing the word
"Warning". That inconsistency should be resolved in the same pass.

## Scope boundary

- **Inverse defect, same function:**
  [claim-push-reports-success-when-rebase-drops-identical-racing-claim](../claim-push-reports-success-when-rebase-drops-identical-racing-claim/)
  is the false *negative* — a rebase that exits 0 while a real race happened.
  This card is the false *positive*. Distinct root causes and distinct fixes,
  but Option B above would supply the card-derived evidence that card also
  needs, so whichever lands first should be read by the other.
- **Not a meta-fix.** The "collapse a subprocess exit code into one semantic
  cause" shape has exactly two instances in `engine.py`: the closed
  `closure_on_integration` card and this one. The remaining `returncode`
  sites either report git's own diagnostic (`goc/engine.py:5188`, `:4563`) or
  fail toward surfacing the real error (`goc/engine.py:4942`, `:5052`). Two
  instances, one already fixed, is a concrete card — not an architectural
  umbrella.
- **Not about `worker` persisting.** That the field outlives a claim is
  intended and documented; the defect is reading it as a live claim-holder
  without checking `status`.
