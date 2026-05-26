---
title: advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose
summary: |-
  `advanced-by-closed` (and the about-to-land derived dependency-
  readiness) treat EVERY `advanced_by` edge as a hard
  closure/readiness prerequisite. But the design card
  `rename-blocks-to-advances-and-design-value-sort` defines the edge as
  "~80% value contribution, ~20% strict prerequisite," with the
  strict/loose distinction "carried by the body, not the field." So the
  hard reading over-reads the loose majority: in a densely-linked deck,
  aggregator-epics with `advanced_by` up to 24 are each held closed
  until every contributor closes, even where an edge means "this
  informed that," not "this blocks that." This is a maintainer call
  about what `advanced_by` *means* — it can't be fixed in attest alone
  because the same reading drives the epic's own derived-readiness
  decision. Parked for a decision.
status: open
stage: null
contribution: high
created: "2026-05-26T04:55:34Z"
closed_at: null
human_gate: decision
advances:
  - blocked-status-conflates-dependency-external-wait-and-deferral
advanced_by: []
tags: [api-contract, documentation]
definition_of_done: |
  - [ ] A chosen option is recorded in this body (`## Decision`) with
        its reason, and the gate dropped to `none`.
  - [ ] The decision is applied coherently to BOTH surfaces that read
        `advanced_by` as a dependency: `advanced-by-closed` (attest) and
        the derived dependency-readiness in
        `derive-dependency-readiness-instead-of-storing-blocked-status`
        — not attest alone.
  - [ ] If the decision changes the edge schema or the check's severity,
        `card-schema` / `advance-card` skills and the default
        `config.yaml` are updated to match, and `goc validate` stays
        green.
  - [ ] A regression fixture demonstrates the chosen behaviour on a
        loose aggregation edge vs. a strict prerequisite edge.
---

# `advanced_by` is read as a hard prerequisite, but documented as mostly a loose contribution

## Origin

Second-pass report from a contributor running goc 0.0.20, after the
first report's `advanced-by-closed`-is-buggy framing was corrected. The
check is *mechanically* correct; this card is about the semantics it
assumes. Split out from the authoring/lint guardrail
[`no-guardrail-for-canonical-epic-edge-direction`](../no-guardrail-for-canonical-epic-edge-direction/),
which fixes the backwards-modeling problem and explicitly does **not**
touch the check.

## The tension

`advanced-by-closed` (`goc/engine.py` `_run_derived_check`) fails
closure of card `C` while any card in `C.advanced_by` is not `done` —
treating every `advanced_by` entry as a hard closure prerequisite. It
ships in the default config (`templates/game_of_cards/config.yaml`,
`layer_3_goc_dod`), so every adopter inherits it.

But the design card `rename-blocks-to-advances-and-design-value-sort`
deliberately defines `advances`/`advanced_by` as **~80% loose value
contribution, ~20% strict prerequisite**, and states the strict/loose
distinction "was always carried by the body, not the field" — the
schema-level distinction was *dropped on purpose* to stop `blocks`
reading adversarial. So the field genuinely cannot tell a hard
prerequisite from a loose "this informed that," yet `advanced-by-closed`
reads all of them as hard.

In a densely-linked deck this bites constantly. The contributor's
downstream deck has aggregator-epics with `advanced_by` of 24
(`a5-homeostat-unification`) and 19 (`kappa-readout-canonical-form`);
each is held closed until *every* contributor closes. Correct for a
true aggregation epic — wrong wherever the edge is a loose contribution.

## Why this needs a human decision (not a blind pick)

The same `advanced_by`-means-hard-prerequisite reading is **already
baked into the blocked-status epic's recorded decision** (`blocked-
status-conflates-…` body: "a card with any non-terminal `advanced_by`
prereq is computed blocked-by-dependency"). Its child
`derive-dependency-readiness-instead-of-storing-blocked-status` will
make `next-card`/`pull-card` treat any non-terminal `advanced_by` as
"not ready." So whatever we decide here co-determines whether that
child over-fires the same way attest does. Deciding it for attest in
isolation would split-brain the two surfaces. And Option A below
directly reverses a deliberate simplification from the value-sort
design — that is exactly the kind of axiom-in-tension call a human
should make, not an agent.

## Decision required

### Reasoning

`advanced_by` was deliberately defined as mostly-loose with strict/loose
carried by prose, yet two engine surfaces (attest closure gate; derived
dependency-readiness) read it as strictly hard. Picking blindly risks
either (a) re-introducing schema complexity the value-sort redesign
removed on purpose, or (b) silently keeping a closure/readiness blocker
that the design says should not exist for ~80% of edges. The choice
trades schema simplicity against gate accuracy and must be applied to
both surfaces at once.

### Option A — encode strict-vs-loose per edge

One-line: add an optional per-edge marker (e.g. `advances` entries may
carry a `strict: true` flag, or a parallel `requires` list); gates
(attest + readiness) fire only on strict edges.

- **Pros**
  - Most precise: the gate matches reality edge-by-edge.
  - Lets a genuine prerequisite still hard-block while loose
    contributions don't.
- **Cons**
  - Re-introduces the exact strict/loose schema distinction
    `rename-blocks-to-advances` deliberately *removed* ("carried by the
    body, not the field") — reverses a settled design decision.
  - Migration cost: every existing edge is implicitly loose; someone
    must mark the strict minority or accept silent semantic drift.
  - More frontmatter surface, more validator rules, more to teach.
- Preview: schema change in `goc/schema.yaml` + emitter in
  `goc/engine.py` (`_BLOCK_LIST_FIELDS` / edge rendering) +
  `_run_derived_check` filters to strict edges. Non-trivial.

### Option B — make `advanced-by-closed` advisory / severity-configurable

One-line: downgrade the check from a hard FAIL to a non-blocking
warning (or add a config knob for its severity), and apply the same
"advisory" stance to derived readiness; align attest with what
`goc done` actually enforces (it does *not* gate on this check).

- **Pros**
  - Honest to the design: the field can't distinguish, so don't pretend
    at gate-time; keep the signal as information, not a block.
  - Smallest change; no schema growth; no migration.
  - Removes the autonomous-worker halt and the per-child `--skip` toil.
- **Cons**
  - Loses a genuine guard for the ~20% that *are* strict prerequisites
    (a real out-of-order closure would only warn).
  - "Advisory" needs a clear convention so it isn't ignored noise.
- Preview: in `templates/game_of_cards/config.yaml`, mark the check
  advisory (new `severity: warn` field consumed by `_cmd_attest`), or
  drop it from `layer_3_goc_dod` by default. `_run_derived_check`
  unchanged; `_cmd_attest` stops counting it toward `any_failed`.

### Option C — gate only when the upstream card is itself blocking

One-line: `advanced-by-closed` fails only when an unclosed
`advanced_by` card is *itself* impeded (`human_gate != none` or
`status: blocked`); otherwise it's informational.

- **Pros**
  - No schema change; narrows the FAIL to cases where ordering plausibly
    matters.
  - Keeps a hard block for the "parked parent" shape.
- **Cons**
  - Still a heuristic — proxies "is this a real prerequisite?" by the
    upstream's gate/status, which is not the same thing.
  - Couples the check to gate semantics, harder to explain.
- Preview: `_run_derived_check` reads each upstream card's
  `human_gate`/`status` before counting it as a blocker.

### Option D — keep the hard reading (status quo)

One-line: accept that every `advanced_by` is a hard prerequisite for
closure and readiness; the friction is the cost of a simple field.

- **Pros**
  - Zero work; matches the epic's already-recorded readiness premise.
  - Strongest closure ordering guarantee.
- **Cons**
  - Contradicts the design card's own "~80% loose" definition.
  - The friction (per-child `--skip`, autonomous-worker halt on
    clusters) is exactly what the contributor reports.

### Recommendation

**Option B** (advisory / severity-configurable, applied to both attest
and derived readiness). It respects the deliberate "no per-edge schema
distinction" decision while ending the over-read, is the smallest
change, and aligns attest with what `goc done` already enforces. The
dominant driver: the field was *designed* not to distinguish strict
from loose, so a hard gate on it is reading information the field does
not carry. Not binding — if preserving a hard ordering guard for true
prerequisites matters more than schema simplicity, Option A is the
precise (but heavier) alternative.
