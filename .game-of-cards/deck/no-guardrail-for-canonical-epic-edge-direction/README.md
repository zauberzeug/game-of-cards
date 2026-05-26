---
title: no-guardrail-for-canonical-epic-edge-direction
summary: |-
  The canonical way to model an epic is `child.advances: [epic]` (work
  serves the goal), which the bidirectional invariant turns into
  `epic.advanced_by: [children]`. This is documented once in
  card-schema (SKILL.md "This axis subsumes hierarchy…") and never
  surfaced at authoring time, and nothing detects the inverted shape.
  An author reaching for the intuitive "parent points down to its
  children" files `epic.advances: [children]`, forcing
  `child.advanced_by: [epic]`. That inversion silently (1) defeats the
  value law — children no longer inherit the epic's value, so the GRPW
  sort can't see the chain — and (2) trips a spurious
  `advanced-by-closed` attest FAIL on every child of an open epic,
  because the child now reads as gated on a parent that is meant to
  outlive it. Surface the canonical direction at authoring time and add
  a `goc validate` lint for the backwards shape. Do NOT change the
  `advanced-by-closed` check — it is correct under the documented
  convention.
status: open
stage: null
contribution: medium
created: "2026-05-26T04:41:02Z"
closed_at: null
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [ ] `create-card` and `card-schema` skills state the canonical epic
        direction loudly at the point of authoring: epic membership is
        `child.advances: [epic]` (work serves goal), never
        `epic.advances: [children]`. Include the two consequences of
        inverting it (value law defeated; spurious attest FAIL).
  - [ ] `goc validate` emits a hint (warning, not error) when a card's
        `advances` lists a card that, by tags/shape, it appears to
        *aggregate* rather than *serve* — i.e. the likely-backwards
        epic edge. The hint names both cards and the corrective edit.
  - [ ] The hint does not fire on this repo's own correctly-modeled
        epic (`blocked-status-conflates-…` with `advanced_by: [3
        children]`, children with `advances: [epic]`).
  - [ ] `advanced-by-closed` (engine `_run_derived_check`) is left
        unchanged — verified by reading the check and confirming it is
        correct under the documented convention.
  - [ ] reproduce.py (or a fixture) shows: backwards model trips the
        lint + a child attest FAIL; canonical model passes both.
  - [ ] A pointer is added to the `blocked-status-conflates-…` epic
        body: the "is `advanced_by` a hard prerequisite or a loose
        contribution?" severity question is its decision to make, once,
        across both `attest` and the derived-readiness feature — not a
        standalone attest tweak.
---

# Nothing steers epic authors to the canonical edge direction

## Origin

A contributor running goc 0.0.20 reported that `goc attest` blocks
closure of every child of an open epic/umbrella card: the layer-3
`advanced-by-closed` check FAILs with "1 not done: <parent>". They
proposed exempting or softening the check.

Investigation against this repo's engine and deck shows the check is
**correct**; the report's root-cause framing is inverted from GoC's
documented convention. The real gap is that the convention is neither
surfaced at authoring time nor lint-enforced, so authors fall into the
backwards shape and hit the symptom.

## The canonical direction (already documented, never surfaced)

`card-schema/SKILL.md` ("This axis subsumes hierarchy…") states the
law: an epic that aggregates its sub-stories' contributions is just the
epic having `advanced_by: [story-1, story-2, …]`. By the bidirectional
invariant that means **`child.advances: [epic]`** — the work card
*serves* the goal. This repo's own epic models it exactly so:

```
epic    blocked-status-conflates-…    advances: []         advanced_by: [c1, c2, c3]
child   derive-dependency-readiness   advances: [epic, …]  advanced_by: []
```

Under this model the reported symptom does not exist:

- A **child** has `advanced_by: []` → `advanced-by-closed` returns
  "no advanced_by edges" → PASS. Children close freely.
- The **epic** has `advanced_by: [children]` → the check holds it open
  until the children are done — which is literally the epic's own DoD
  (`- [ ] Child X closed`). Correct.

## The inverted shape and its two silent costs

The intuitive-but-wrong model is `epic.advances: [children]` ("the
parent points down to its children"), which forces
`child.advanced_by: [epic]`. Two things break, both silently:

1. **Value law defeated.** `value(c) = max(rank(c), γ·max(value(d) for
   d in c.advances))`. With the canonical edge, a child advances the
   high-value epic and *inherits* that value, so the GRPW sort ranks
   epic work correctly. Inverted, the child advances nothing and the
   epic merely inherits its highest child's value — useless for
   prioritisation, and the chain the sort was built to see is gone.
2. **Spurious `advanced-by-closed` FAIL.** The child now lists the epic
   in `advanced_by`, so attest reads the child as gated on a parent
   that is *meant to outlive it*. `finish-card` documents that FAIL as
   a closure blocker, so every epic-child closure needs a manual
   `--skip` + justification, and an autonomous `pull-card`/`/loop`
   worker halts on the whole cluster.

When the parent is `human_gate: decision` (parked for a human) or an
epic whose own DoD waits on its children, the inverted model is a hard
deadlock: child waits on parent, parent waits on child.

## Why not change the check

The contributor's resolutions #1 (gate/tag exemption) and #2
(topological exemption) special-case around a misuse and would weaken
the check for *genuine* prerequisites that happen to be parked. #3
(downgrade to warning) deletes a correct guard to cure backwards
modeling. #4 ("epic membership MUST be `child.advances: [parent]`") is
not a future migration — it is *already the documented law*; it just
isn't loud or enforced. This card implements #4 as guidance + lint and
leaves the check alone.

## Interaction with the blocked-status epic

`derive-dependency-readiness-instead-of-storing-blocked-status` (open,
child of `blocked-status-conflates-…`) is about to make `next-card` /
`pull-card` read `advanced_by` terminality as a hard "not ready"
signal. If epics are modeled backwards, that new feature derive-blocks
every epic child too — so this guardrail protects the in-flight work,
which is why it advances that epic.

The deeper question the report raises in passing — `advances`/
`advanced_by` is documented as ~80% loose contribution, ~20% strict
prerequisite, so should `advanced-by-closed` be a hard FAIL at all? —
is real but must be answered *once*, coherently, across both `attest`
and derived readiness. That belongs to the blocked-status epic's
decision, not to this card.

## Reproduction (minimal)

Canonical (should pass): epic `E` with `advanced_by: [C]`; child `C`
with `advances: [E]`, `advanced_by: []`, DoD 100%. `goc attest C` →
`advanced-by-closed` PASS. `goc validate` → no hint.

Backwards (should warn + fail): epic `E` with `advances: [C]`; child
`C` with `advanced_by: [E]`, DoD 100%. `goc attest C` →
`advanced-by-closed` FAIL. `goc validate` → backwards-epic-edge hint
naming `E` and `C`.
