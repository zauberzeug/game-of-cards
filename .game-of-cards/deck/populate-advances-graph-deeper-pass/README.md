---
title: populate-advances-graph-deeper-pass
summary: |-
  Follow-up to `rename-blocks-to-advances-and-design-value-sort`.
  The mechanical rename + GRPW sort shipped in v3, but most cards
  (296 of 332) have empty `advances`/`advanced_by` lists. Result:
  the GRPW algorithm degenerates to per-card contribution + age,
  i.e. behaves identically to the pre-v3 sort. The amplification
  pathway is structurally live but empirically dormant.
  This card is the editorial pass: read each open card's body,
  identify direct value-flow targets the old `blocks` reading
  discouraged ("X serves Y", "X unblocks Y", "X is a step in Y"),
  and add them as `advances` edges. Bound: only DIRECT relationships
  (no transitive epic cross-references).
status: done
stage: null
contribution: medium
created: 2026-05-03
closed_at: 2026-05-03
human_gate: session
advances: []
advanced_by: []
tags: [epic, infra]
definition_of_done: |
  - [x] **Survey baseline**: run `deck.py --json | jq` to count cards with non-empty `advances` or `advanced_by`. Baseline: 36 of 116 open (31%); 53 of 332 all-status (16%).
  - [x] **Editorial sweep, open cards first**: walked every open isolate (80 cards); 4 parallel Explore agents proposed body-anchored edges; applied 28 edges total across Pass 3a/3b/3c/3d after filtering out invented sink names.
  - [x] **Epic completion**: 3 orphan epics rationalized in body (multi-task-pong-variant: decision-gated, children file later; finish-card-records-implicit-dod-attestation: leaf-level GoC tooling; populate-advances-graph-deeper-pass: this card itself).
  - [x] **Meta-fix family rosters**: framework-summary-stale-implementation-claims-meta-fix wired with 3 sibling-card instances from body table; snapshot-restore-meta-fix-overdue already had 4 advances + 3 new advanced_by from Pass 3 isolate sweep; paper-claim-vs-doc-drift-meta-fix already had 15 wired (now 21+).
  - [x] **Sanity check the sort**: `deck.py -v | head -20` shows top-5 = native high (value=9.0), and spot-checked medium isolates lifted to 6.3 with explicit value_path through paper-claim-vs-doc-drift-meta-fix or framework-summary-stale-implementation-claims-meta-fix. GRPW amplification empirically working.
  - [x] **Closure metric**: 65 of 116 open cards (56%) — ≥45% target reached. +29 cards-with-edges delta vs baseline.
  - [x] One editorial commit; no code changes.
---

# populate-advances-graph-deeper-pass

## Background

The May 3 schema redesign (`goc-rename-blocks-to-advances-and-design
-value-sort`) shipped:

1. Renamed `blocks`/`blocked_by` → `advances`/`advanced_by` (semantic
   shift from strict-prereq to value-contribution).
2. Renamed `impact` → `contribution` (atomic-by-name; reframed
   defect-anchored definition to value-anchored).
3. GRPW + γ=0.7 + tiebreak sort algorithm with `-v` VALUE / WHY
   propagation trace visible.

But it did NOT populate the value graph. Of 332 cards, only 53 have
any edge declared (`advances` or `advanced_by` non-empty); 279 cards
are graph-isolates. For an isolate, the GRPW recursion yields
`value(c) = contribution_rank(c)` — identical to the pre-v3
sort. The amplification pathway is structurally live but empirically
dormant.

## Why this matters

A medium-contribution card on a long chain to a high-contribution
sink should outrank an isolated medium card (`value` 6.3 vs 3.0).
Without populated edges, this never happens; pull-card sees a flat
landscape sorted only by per-card rank. The motivating example —
`pong-soft-bound-tgc-test` (medium) advancing
`pong-late-hr-recovery` (high) advancing `epic-pong` (high) — only
gets the proper ranking once the chain is declared.

## Scope

**In-scope** (do):
- Direct edges only ("X advances Y" where Y is the *immediate next
  step* in the value chain, not Y three hops away).
- Open cards (status `open`/`active`/`blocked`).
- Anchor each addition in body text — never invent a relationship
  the body doesn't support.

**Out-of-scope** (don't):
- Transitive cross-references (epic-of-epic chains; let the GRPW
  recursion compose).
- Done/superseded/disproved cards (forensic, not in the draw pile).
- Renaming or moving cards (that's `improve-deck` hygiene).

## Approach

Three-pass editorial sweep:

### Pass 1 — Epic backfill

Every `tags: [..., epic]` card is a value sink. Surface orphan
epics; for each, scan the deck for cards whose body declares
membership/contribution and wire them via `deck.py advance <epic>
--by <child>`. Surfacing query:

```bash
uv run python .claude/skills/deck/deck.py --tag epic --json | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d:
    if not (c.get('advanced_by') or []):
        print(f'orphan epic: {c[\"title\"]}')
"
```

### Pass 2 — Meta-fix family rosters

Every `tags: [meta-fix]` card lists its family roster in body prose
(e.g. `paper-claim-vs-doc-drift-meta-fix` lists 13+ instance titles).
Convert each roster entry to a structured `advances` edge.

```bash
uv run python .claude/skills/deck/deck.py --tag meta-fix --json | \
  python3 -c "
import json, sys
d = json.load(sys.stdin)
for c in d:
    n = len(c.get('advances') or [])
    print(f'{c[\"title\"]}: {n} instances wired')
"
```

### Pass 3 — Free-text scan

For each remaining open card with empty `advances`, read the body
for phrases like "this serves X", "this unblocks Y", "next step
toward Z", "blocks/blocking Y", "spawned to address Y". Each match
is a candidate direct edge.

This is the long tail; scope-limit by setting a quota
(e.g. 30 minutes / 50 cards reviewed per session) rather than
trying to do all 279 in one pass.

## Cross-references

- Parent: [`rename-blocks-to-advances-and-design-value-sort`](../rename-blocks-to-advances-and-design-value-sort/) — the v3 schema redesign that this populates.
- Tooling: `deck.py advance <title> --by <other>` is the bidirectional-edge mutation.
- Surfacing: `Skill(improve-deck)` already scans for epic/meta-fix orphans (see `## Orphaned dependencies` heuristics there).

## Why this is a separate card

The parent card's DoD scoped commit 4 to "review whether the
migrated entries correctly capture *direct* value contribution."
The migrated entries (53 cards' worth) ARE honest — spot-checked at
v3 ship time and they read as legitimate value flow. What's left
is the *positive* editorial work — adding edges the old `blocks`
reading suppressed — which is genuinely substantial (potentially
days of work) and benefits from being separately tracked, paced,
and (potentially) bot-assisted via the `improve-deck` orphan
detector.

## Orphan-epic note

This card is itself the editorial pass. The `epic` tag is editorial
grouping with sibling `goc-*` infrastructure work, not a
child-aggregator declaration. Empty `advanced_by` is correct: there
are no "instances of populate-advances-graph" — there is just this
one pass.
