---
title: closed-card-relationship-edges-stay-first-class-in-the-deck-graph
summary: "The deck is both a scheduler and a decision record, but its relationship graph is maintained only for the scheduler. Closed-card edges silently degrade the value walk, supersession has no machine-navigable successor pointer, and the record-axis rationale is undocumented."
status: open
stage: null
contribution: medium
created: "2026-05-24T03:57:21Z"
closed_at: null
human_gate: none
advances: []
advanced_by:
  - rename-blocks-to-advances-and-design-value-sort
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [ ] Decision recorded below: how the successor pointer is modelled (new typed field vs. reuse of the advances graph vs. prose-only), and what `compute_values` does on a dangling `advances` target (warn / validate-error / silent).
  - [ ] `compute_values` no longer degrades silently on an unknown `advances` target: a dangling edge is surfaced (warning emitted and/or reported by `goc validate`), so priority math cannot rot unnoticed. (engine.py:1258)
  - [ ] Supersession exposes a machine-navigable successor link per the recorded decision: a reader (human or `--json` consumer) landing on a `superseded` card can be routed forward without parsing log.md prose.
  - [ ] Relationship edges involving closed cards are documented as first-class: AGENTS.md (or the deck README) states the scheduler-vs-record dual purpose and that closed-card edges are maintained for the record axis, so the "discard pile owes no graph" shortcut is not re-derived.
  - [ ] If a new typed field is chosen: schema.yaml, the card-schema skill body, validation, and the block-style/flow YAML emitter all cover it; `goc validate` enforces its invariant. If the advances graph is reused: the semantic overload is documented.
---

# Closed-card relationship edges are first-class members of the deck graph

The deck serves two jobs at once, and its relationship graph is currently
maintained for only one of them.

- **Scheduler axis** — *what do I work on next?* Reads only edges among live
  cards. The GRPW value sort (`compute_values`, `engine.py:1216`) walks
  `advances` to compose priority.
- **Record axis** — *how and why did we get here?* A reader — increasingly an
  LLM doing a cold read — reconstructs the history of a decision by walking
  edges, including edges that sit entirely inside the discard pile
  (`done` / `disproved` / `superseded`).

The live design optimises for the scheduler and quietly under-serves the
record. That produces one latent bug, one missing capability, and one
undocumented policy. This card is the umbrella for all three because they
share a single root: **a relationship edge's value does not end when a card
closes — referential integrity is a property of the edge, not of either
endpoint's liveness.**

## Thread 1 — silent value-walk degradation on dangling edges (bug)

`compute_values` skips any `advances` target it cannot resolve:

```python
for dest in t.frontmatter.get("advances") or []:
    if dest not in by_title:
        continue          # engine.py:1258 — silently dropped
```

If an edge target is renamed or deleted (or an edge rots because the other
endpoint was treated as "out of play" and not kept consistent), the walk
drops it with no signal. Priority math degrades and nobody sees it — strictly
worse than a loud half-edge error. The docstring even advertises this:
"Unknown advances targets are silently skipped" (`engine.py:1241`). Note this
fires for genuinely-missing/renamed targets; closed cards are loaded normally,
so the failure mode is *edge rot and stale references*, not merely closure.

## Thread 2 — supersession has no machine-navigable successor pointer (capability)

Supersession is recorded as **log.md prose plus a body pointer** (advance-card
skill: on `* → superseded`, "append entry naming and linking the successor
card"). There is no typed successor field in the schema — the only relationship
fields are `advances` / `advanced_by`. So a reader landing on a `superseded`
card cannot be *mechanically* routed to its replacement; they must read prose.

This is the gap relative to the dominant prior art (see below): the convention
is a typed, bidirectional, auto-symmetric successor link *for the pointer*,
with prose *for the rationale* — both, for different jobs. The deck has the
prose half and lacks the typed half.

## Thread 3 — the record axis is undocumented (policy / doc)

Nothing in AGENTS.md or the deck README states that closed-card edges are
maintained deliberately, for the record axis. Absent that, the next
contributor re-derives the plausible-but-wrong shortcut: "closed cards are out
of active play, so the deck owes no relationship graph for them; forensic reads
recover from log.md." That shortcut fails on three counts already present in
the engine: it ignores `STALE_BLOCKED` coherence (which reads closed-card
status, `engine.py:1164`), the value walk traversing chains *through* closed
cards, and retroactive edges (a closed card *can* gain a new outbound
`advances` edge when value is discovered after the fact — this very card was
filed `--advanced-by` a `done` card to demonstrate exactly that).

## Why it matters

The cost structure is asymmetric. Recording a typed edge is an O(1) write at
the moment the relationship is known and cheapest to state. Reconstructing a
lost relationship later from prose is O(read-everything) and lossy — inferring
structure that was once explicit. "Forensic reads recover from log.md"
under-prices the forensic read and over-prices the edge. For a methodology
whose readers are AI agents, a traversable typed graph beats scattered
per-card prose decisively.

The sharpest failure mode is **rot**, not absence: a partially-maintained graph
makes a missing edge ambiguous — "no relationship existed" vs. "edge dropped on
close" — which poisons the reconstruction the record axis exists to serve.

## Prior art

The two most relevant patterns both treat supersession as a typed,
bidirectional, machine-navigable link applied at closure — not as prose:

- **Architecture Decision Records.** A superseded ADR's status becomes
  `Superseded by ADR-XXXX` with a link, and the successor links back; tooling
  (adr-tools, Log4brains) parses these to render back-links. ADRs have *no
  scheduler function at all* — their link graph is purely forensic, and the
  practice keeps it precise anyway. This alone proves the record axis justifies
  the graph.
  ([Fowler](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html),
  [joelparkerhenderson/architecture-decision-record](https://github.com/joelparkerhenderson/architecture-decision-record))
- **Issue trackers** (Jira, YouTrack, Google Issue Tracker). Supersession-class
  relationships (`duplicates` / `is duplicated by`, custom `superseded by`) are
  first-class typed links, created *at close time*, with both ends written
  automatically on one action — which dissolves the "extra invariant to
  hand-maintain" objection.
  ([YouTrack](https://www.jetbrains.com/help/youtrack/server/link-issues.html),
  [Atlassian](https://confluence.atlassian.com/adminjiraserver/configuring-issue-linking-938847862.html),
  [Google Issue Tracker](https://developers.google.com/issue-tracker/guides/duplicate-issue))

## Decision

*Resolved 2026-05-24T04:05:00Z:* A1 (typed bidirectional superseded_by/supersedes field) + B1+B2 (compute_values warns AND goc validate errors on dangling advances targets)

*Reasoning:* Typed successor link matches ADR/issue-tracker convention and makes supersession machine-navigable; surfacing dangling edges both at compute time (warn) and in validate (error) makes edge rot impossible to miss, not merely visible.
