---
title: dod-100-percent-derived-check-passes-free-form-dod-that-goc-done-refuses
summary: "`_run_derived_check('dod-100-percent', ...)` returns `(True, 'freeform DoD')` whenever the card's DoD is free-form prose, so `goc attest` writes a `## Closure verification` block whose `[x] dod-100-percent — freeform DoD` row claims the card passed the completeness check. `goc done` (and `goc done --bundle`) then refuse the same card with `ERROR: free-form DoD; use --force to bypass enforcement`. Two verbs disagree on the same predicate."
status: open
stage: null
contribution: high
created: "2026-05-31T04:08:34Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero (defect no longer fires) — current behavior asserted, then re-asserted after the fix
  - [ ] PROCESS: decision recorded in this card's `## Decision required` section — which of attest / done changes to resolve the contradiction, and what verdict `dod-100-percent` reports on free-form DoD
  - [ ] MECHANICAL: `_run_derived_check` for `dod-100-percent` and `_cmd_done` / `_cmd_done_bundle` agree on free-form DoD; their disagreement is gone in code
  - [ ] TDD: a new regression test in `tests/` exercises a free-form DoD card and asserts attest + done are consistent under the chosen contract
  - [ ] MECHANICAL: `goc validate` passes
---

# `dod-100-percent` derived check passes free-form DoD that `goc done` refuses

## Location

- `goc/engine.py:4054-4059` — `_run_derived_check("dod-100-percent", ...)`
- `goc/engine.py:3492-3494` — `_cmd_done` free-form refusal
- `goc/engine.py:3566-3571` — `_cmd_done_bundle` free-form refusal

## What's broken

`_run_derived_check` treats a free-form DoD as a passing check:

```python
if name == "dod-100-percent":
    if card.dod_freeform:
        return True, "freeform DoD"
    if card.dod_open > 0:
        return False, f"{card.dod_open} unchecked boxes"
    return True, f"{card.dod_done}/{card.dod_done} ticked"
```

But the close-the-card verbs treat the same free-form DoD as a hard
stop that requires explicit override:

```python
# _cmd_done
if t.dod_freeform and not force:
    print(f"ERROR: {title}: free-form DoD; use --force to bypass enforcement", file=sys.stderr)
    sys.exit(2)
```

```python
# _cmd_done_bundle
if t.dod_freeform and not force:
    print(
        f"ERROR: {title}: free-form DoD; use --force to bypass enforcement",
        file=sys.stderr,
    )
    sys.exit(2)
```

So `goc attest` writes `[x] dod-100-percent — freeform DoD` into the
`## Closure verification` block of `log.md` and prints `Attestation OK.`,
but the immediately-following `goc done` exits 2 and refuses to close
the card. The two verbs disagree on the same predicate (`is this
free-form DoD acceptable as a closure signal?`) on the same card.

## Empirical evidence

Run on a scratch repo with one card whose DoD is free-form prose (see
`reproduce.py`):

```
--- goc attest ---
exit: 0
stdout tail:
  - [x] dod-100-percent — freeform DoD
  ...
  Attestation OK.

--- goc done ---
exit: 2
stderr:
ERROR: sample-card: free-form DoD; use --force to bypass enforcement
```

## Reachability

- A consumer writes a card whose work doesn't reduce to a checklist
  (a research spike, an open-ended doc rewrite, an "explore X" task)
  and intentionally leaves the DoD as free-form prose.
- They run `goc attest` to record verification and see `Attestation OK`
  plus a written `## Closure verification` row with `[x] dod-100-percent
  — freeform DoD`.
- They then run `goc done` and are surprised by the refusal. The
  attestation row is now a lie in the historical record: `log.md`
  claims the completeness check passed on a card the engine itself
  refuses to mark complete without `--force`.

## Why it matters

`dod-100-percent` is the engine's own statement about whether the
card's completeness criteria are met. `goc done`'s `--force`-gate on
free-form DoD is the engine's other statement about the same thing.
They contradict — one says "passed," the other says "unverifiable
without operator override." The attestation block, once written, is
durable evidence in `log.md` that a derived check passed; that
evidence is false whenever it sits on a free-form-DoD card.

This is the same failure-mode family as the recently-closed
[goc-attest-reports-ok-and-writes-empty-stub-when-no-checks-are-configured](../goc-attest-reports-ok-and-writes-empty-stub-when-no-checks-are-configured/):
a closure-verification verb reporting `Attestation OK` and writing a
PASS row to disk on content that does not actually verify the card.
Sibling cards in the same area —
[bundled-closure-skips-configured-attestation-checks](../bundled-closure-skips-configured-attestation-checks/),
[goc-attest-mutates-log-md-on-already-closed-cards](../goc-attest-mutates-log-md-on-already-closed-cards/),
[goc-attest-silently-ignores-unknown-skip-names](../goc-attest-silently-ignores-unknown-skip-names/) —
share the same shape.

## Decision required

The contradiction can be resolved in one of three directions. Each
keeps attest and done aligned on the same predicate; they differ in
what story they tell the consumer about a free-form DoD.

1. **Attest reports SKIPPED.** Change `_run_derived_check` so
   `dod-100-percent` on a free-form DoD returns the sentinel that
   `_format_attestation_block` already renders as `[~] ... SKIPPED —`
   (see `engine.py:4108-4110`). `Attestation OK` stays correct
   (no failure, just one skip). `goc done` continues to require
   `--force`, consistent with "the engine cannot verify completeness;
   the human must assert it." Recommended baseline: it makes the
   skip visible in `log.md`, matches `done`'s posture, and reuses
   existing rendering infrastructure.

2. **Attest fails.** Return `(False, "free-form DoD requires --force on done")`.
   `goc attest` exits non-zero, matching `goc done`'s exit-2 refusal.
   Strictest option; surfaces the free-form-DoD card as immediately
   unfit for closure-verification automation.

3. **Done accepts attested free-form.** Drop the `--force` gate on
   `_cmd_done` / `_cmd_done_bundle` when the card has a fresh
   `## Closure verification` block in `log.md` whose `dod-100-percent`
   row passed. Most lenient option, but inverts the trust direction
   (attest becomes the override for done's refusal) and tangles
   `_cmd_done` with `log.md` parsing.

## Fix

The fix is single-site once a direction is chosen:

- Options 1 and 2 edit only `_run_derived_check` (`engine.py:4054-4059`)
  plus add a regression test.
- Option 3 edits `_cmd_done` / `_cmd_done_bundle` (`engine.py:3492-3494`,
  `engine.py:3566-3571`) plus add a regression test.

Either way, the regression test in `tests/` should construct a
free-form-DoD card and assert that `goc attest` and `goc done` agree:
either both report a passing/closing path or both refuse, depending
on the chosen direction.
