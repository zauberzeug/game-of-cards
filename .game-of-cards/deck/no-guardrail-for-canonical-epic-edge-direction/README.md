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
  outlive it. A second, related miss: not every coordinating card is an
  aggregation epic. A *governing* card — a decision/standard-setting
  card that closes when decided, independent of the work it standardizes
  — has no hard ordering in either direction, so NO `advances` edge
  models it (either direction deadlocks or contradicts the decision's
  DoD); the faithful encoding is a shared *tag*. Surface, at authoring
  time, both the aggregation-edge direction AND the edge-vs-tag fork, and
  add a `goc validate` lint for the backwards/over-edged shape that
  suggests the *right* fix (flip vs. convert-to-tag). Do NOT change the
  `advanced-by-closed` check — it is correct under the documented
  convention.
status: done
stage: null
contribution: medium
created: "2026-05-26T04:41:02Z"
closed_at: "2026-05-26T06:01:47Z"
human_gate: none
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
  - validate-backwards-epic-edge-fix-suggestion-has-swapped-command-arguments
advanced_by: []
tags: [documentation, api-contract]
definition_of_done: |
  - [x] `create-card` and `card-schema` skills state, at the point an
        edge is authored, the three-way fork for a coordinating card:
        (a) **aggregation epic** — its value chain *is* its children;
        closes when they close → `child.advances: [epic]`;
        (b) **governing cluster** — a decision/standard card that closes
        when decided, independent of the governed work → a shared
        **tag**, no `advances` edge in either direction;
        (c) never `epic.advances: [children]` (the backwards bug).
        Include the consequences: backwards defeats the value law + trips
        a spurious attest FAIL; a wrong edge on a govern-cluster
        deadlocks one way or contradicts the decision's DoD the other.
  - [x] `goc validate` emits a hint (warning, not error) for the
        backwards/over-edged signature: a coordinating card whose
        `advances` targets are predominantly *lower* contribution than
        itself. Use the contribution gradient, NOT a bare `advances ≥ N`
        count (a downstream deck reports 124 live cards with ≥3 advances
        that are legitimate hubs). The hint must offer the *correct* fix,
        not blindly "flip": if the card's closure genuinely waits on the
        work → flip to `child.advances:[card]`; if the card closes
        independently (esp. `human_gate: decision` / a standard-setting
        card) → drop the edge and group with a shared tag.
  - [x] The hint does not fire on (a) this repo's own correctly-modeled
        aggregation epic (`blocked-status-conflates-…`), nor (b) a
        legitimate hub advancing many higher-or-equal contribution
        targets.
  - [x] `advanced-by-closed` (engine `_run_derived_check`) is left
        unchanged — verified by reading the check.
  - [x] reproduce.py (or fixtures) covers all three shapes: backwards
        aggregation (lint + attest FAIL) → flip fixes it; govern-cluster
        edge (deadlock one way / DoD-contradiction the other) → tag fixes
        it; canonical aggregation passes clean.
  - [x] Cross-reference the now-decided
        `advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`
        (Option E) so a reader who hits the attest FAIL is routed to the
        value-chain reasoning and the `goc unadvance` retraction path.
worker: {who: "claude[bot]", where: main}
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
below. A third follow-up surfaced the deeper miss: a *governing*
decision card and its instance cluster have no hard ordering either way,
so neither edge direction models them — the fix is a shared tag, not a
flip. That distinction (aggregation epic → edge; govern-cluster → tag)
is now part of this card's scope; see "A coordinating card is one of two
shapes" below.

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

## A coordinating card is one of two shapes — and only one takes an edge

The canonical-direction rule above assumes the coordinating card is an
**aggregation epic**: its value chain literally *is* its children, so it
closes *when they close*. For that shape the edge is right and
`advanced-by-closed` on the epic is correct.

But not every coordinating card is an aggregation epic. A **governing
card** — a decision or standard-setting card that closes *when the
decision is made*, independent of the work it standardizes — relates to
its cluster **softly and two-way**: the cluster motivates the decision;
the decision then standardizes the cluster. There is no hard ordering in
either direction (instances can be fixed before *or* after the standard
is set).

An `advances` edge cannot model that, because one edge encodes **two**
hard, directional commitments at once:

- **value flow** — the source lends its priority to the target (GRPW), and
- **closure gating** — `advanced-by-closed`: the target can't close until
  the source is done.

For a soft, two-way govern relationship *both* commitments are wrong, so
*either* edge direction mismodels it:

| encoding | what `advanced-by-closed` does | verdict |
|---|---|---|
| `decision.advances:[instances]` (=`instance.advanced_by:[decision]`) | blocks each **instance** behind the open decision | deadlock — instances can't close |
| `instance.advances:[decision]` (=`decision.advanced_by:[instances]`) | blocks the **decision** behind all instances | contradicts the decision's DoD (closes when *decided*) |
| **shared tag**, no edge | nothing — pure grouping | **correct**: govern without blocking |

The faithful encoding of "govern but don't block" is a **tag** — zero
value flow, zero closure gating. card-schema already allows this: the
`epic` tag is "multiple cards block it from closing **OR** carry the
same epic-grouping tag." The gap is the *OR* is never surfaced, so
authors reach for an edge even when a tag is the honest tool.

**The tell:** if the coordinating card is a *decision* (`human_gate:
decision`) or otherwise closes on its own deliverable rather than on its
cluster's completion, it is a govern-cluster → use a tag. Reach for an
edge only when the coordinator's closure genuinely waits on the work.

*Worked example (downstream, goc 0.0.20):* a decision card "what is the
canonical form of a plasticity-contract test?" governs 13 instance
tests. Modeled `decision.advances:[instances]`, the instances deadlocked
behind the open decision — yet two had already closed independently,
proving no real dependency. Flipping the edge would instead block the
decision behind all 13, but its DoD closes on *choosing the rule* and
`goc advance`-ing the members to *active* (not *done*). Neither edge is
right; a shared tag is. This is the same retraction Option E prescribes
on the closure card — with the added rule that the *replacement* for the
retracted edge is a tag, not a flip.

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
