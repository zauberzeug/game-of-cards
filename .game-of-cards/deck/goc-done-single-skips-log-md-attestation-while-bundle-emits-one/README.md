---
title: goc-done-single-skips-log-md-attestation-while-bundle-emits-one
summary: "`_cmd_done_bundle` writes a `## Closure verification … — bundled` attestation block AND a `## … — Closure (bundled)` entry to each member card's `log.md`; `_cmd_done` (single) writes nothing. So a card closed singly has no in-card record of closure, while a card closed as part of a bundle has a full attestation table — an asymmetry between two near-twin code paths that both satisfy the same DoD gate. Unverified: may be intentional design (bundle has structured payload — the co-closing-members set — single does not), but worth a decision before the docs documenting `goc attest` diverge further from observable behaviour."
status: open
stage: null
contribution: low
created: "2026-05-30T09:41:51Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [bug, api-contract, unverified]
definition_of_done: |
  - [ ] PROCESS: Decision recorded on whether `_cmd_done` should emit any log.md block (none, a minimal closure marker, or the full attestation `goc attest` writes).
  - [ ] PROCESS: If "yes," `_cmd_done` is updated to match the bundle path's log.md emission OR a reduced shape, and a regression test asserts the file is non-empty post-close.
  - [ ] PROCESS: If "no," the bundle path's automatic attestation emission is reconsidered for consistency, OR the `attest`/`done` separation in the skill docs is updated to explain why bundle implicitly attests and single does not.
---

# goc done (single) writes no log.md; goc done --bundle writes attestation + closure

## Hypothesis (file:line)

- `_cmd_done` at `goc/engine.py:3223-3266` — flips status to `done`,
  sets `closed_at`, prints to stdout. No `log.md` mutation.
- `_cmd_done_bundle` at `goc/engine.py:3338-3346` — for each bundled
  member, unconditionally appends `attestation_block + closure_entry`
  to that member's `log.md` (the attestation block is the same shape
  `goc attest` writes; the closure entry is a `## <ts> — Closure
  (bundled)` block listing the other co-closing members).

Empirically: after `goc done <single>`, `log.md` is empty (or
unchanged). After `goc done --bundle a b`, both `a/log.md` and
`b/log.md` carry the attestation table + a closure block.

## Decision required

Two near-twin closure paths emit different in-card records. Pick one:

1. **Leave as-is + document** — bundle's auto-attestation is an
   intentional convenience because the co-closing-members set is
   structured payload worth recording; single done has no payload
   beyond what frontmatter already captures.
2. **Make single match bundle** — `_cmd_done` should emit at least a
   closure marker (and possibly the full attestation table) so every
   closed card has an in-card history regardless of how it was
   closed.
3. **Strip bundle's auto-attestation** — both paths require an
   explicit `goc attest` invocation if the user wants an in-card
   attestation record; bundle stops doing it implicitly.

## Why deferred (unverified)

The closely-related disproved card
[state-flip-verbs-skip-log-md-entry](../state-flip-verbs-skip-log-md-entry/)
established that CLI silence on status flips is by design: the CLI
writes `log.md` only when it has structured semantic payload. That
lens supports option (1) — bundle records the co-closing-members set,
which IS structured payload, while single done has nothing extra to
record.

But bundle also writes the attestation table (the same shape
`goc attest` writes as a separate verb), which is what makes the
asymmetry feel like more than just "bundle records a list of peers."
A card closed singly requires the user to run `goc attest` first if
they want an in-card attestation; a card closed in a bundle gets one
for free.

## Falsification recipe

1. Re-read the disproved predecessor and `Skill(finish-card)` end-to-end:
   is bundle's automatic attestation an intentional convenience, or a
   doc-undocumented side effect?
2. Probe both paths on a scratch deck and diff the two `log.md` results.
3. Decide per the three options above and update either the code or the
   skill docs.

## Surfaced by

`audit-deck` round, 2026-05-30, `general-purpose` hunter candidate #2
of 3.
