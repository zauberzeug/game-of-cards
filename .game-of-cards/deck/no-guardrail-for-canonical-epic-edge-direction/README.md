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
  - [ ] `goc validate` emits a hint (warning, not error) for the
        backwards-epic signature: a card whose `advances` targets are
        predominantly *lower* contribution than itself (value flowing
        the wrong way — an aggregator pointing down at the work it
        collects). Use the contribution gradient, NOT a bare
        `advances ≥ N` count: a downstream deck reports 124 live cards
        with ≥3 advances that are legitimate hubs, so a count rule
        over-fires. The hint names both cards and the corrective edit.
  - [ ] The hint does not fire on (a) this repo's own correctly-modeled
        epic (`blocked-status-conflates-…` with `advanced_by: [3+
        children]`, children with `advances: [epic]`), nor (b) a
        legitimate hub card that advances many higher-or-equal
        contribution targets.
  - [ ] `advanced-by-closed` (engine `_run_derived_check`) is left
        unchanged — verified by reading the check and confirming it is
        correct under the documented convention.
  - [ ] reproduce.py (or a fixture) shows: backwards model trips the
        lint + a child attest FAIL; canonical model passes both.
  - [ ] The strict-vs-loose severity question is carried by a separate
        decision card
        (`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`,
        `human_gate: decision`, advancing the same epic). This card does
        NOT decide it — it only cross-references it so a reader who hits
        the attest FAIL is routed to the open decision.
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
backwards shape and hit the symptom. A follow-up report from the same
contributor confirmed this diagnosis (the check is correct; the
deadlock came from a backwards-modeled epic) and refined the lint
heuristic to a contribution-gradient signal — folded into the DoD
below.

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

The deeper question the report raises — `advances`/`advanced_by` is
documented as ~80% loose contribution, ~20% strict prerequisite, so
should `advanced-by-closed` be a hard FAIL at all? — is split out to
its own decision card,
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/).
It must be answered *once*, coherently, across both `attest` and the
derived-readiness feature — note the epic's **own recorded decision**
already commits to "any non-terminal `advanced_by` ⇒ blocked-by-
dependency," which is the same hard reading, so the decision card
re-examines a premise the epic depends on. This guardrail card stays
`human_gate: none` and does not wait on that decision.

A third, optional helper the report suggests (not a DoD requirement
here): a `goc epic <epic> --over <child…>` command that writes the
edges in the canonical direction so adopters never hand-roll them.

## Reproduction (minimal)

Canonical (should pass): epic `E` with `advanced_by: [C]`; child `C`
with `advances: [E]`, `advanced_by: []`, DoD 100%. `goc attest C` →
`advanced-by-closed` PASS. `goc validate` → no hint.

Backwards (should warn + fail): epic `E` with `advances: [C]`; child
`C` with `advanced_by: [E]`, DoD 100%. `goc attest C` →
`advanced-by-closed` FAIL. `goc validate` → backwards-epic-edge hint
naming `E` and `C`.
