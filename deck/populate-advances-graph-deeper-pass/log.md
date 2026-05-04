# Log — populate-advances-graph-deeper-pass

## 2026-05-03 — Filed

Filed at the close of `rename-blocks-to-advances-and-design-value-sort`
to track the substantial editorial follow-up of populating the value
graph on 279 graph-isolate cards. The parent shipped the schema +
GRPW algorithm; this card was the editorial pass to make the
amplification empirically alive.

## 2026-05-03 — Closed

### Approach

Three-pass editorial sweep over 80 open isolates + 3 orphan epics +
2 meta-fix cards needing roster wiring. The 80 isolates were split
into 4 parallel Explore-agent batches; each agent read ~20 card
bodies, identified body-anchored value-flow edges to a curated sink
list, and returned JSON proposals.

### Filter discipline

Pass 3a auto-applied 13 well-anchored edges. Pass 3c invented many
sink names (e.g. `silent-state-corruption-meta-fix`, `test-tautology-
family-meta-fix`) that don't exist in the deck — filtered to the 7
real sinks before applying. Pass 3d's agent invented similarly;
salvaged 4 well-anchored edges (snapshot/reset family, pong-soft-
bound parent). Total applied: 28 + 13 (Pass 3a) = 41 edges.

### Pass results

- **Pass 3a (doc-drift, 20 cards)**: 13 edges applied (auto-applied
  by agent), 7 nulls. Sinks dominated by `paper-claim-vs-doc-drift-
  meta-fix` and `f-channel-layer-3b-architectural-gap-decision`.
- **Pass 3b (pong/plasticity, 20 cards)**: 5 edges proposed, all
  applied. Sinks: 4 done sister-cards (semantic legitimate per GRPW
  — done targets still amplify) + 1 open meta-fix.
- **Pass 3c (mechanics, 20 cards)**: 7 of ~12 proposed targets were
  invented; applied the 7 real ones. Sinks: paper-claim-vs-doc-drift-
  meta-fix (3) + framework-summary-stale-implementation-claims-
  meta-fix (3) + snapshot-restore-meta-fix-overdue (1).
- **Pass 3d (tail, 20 cards)**: most proposed targets were invented.
  Salvaged 4 from the snapshot/reset family + pong-soft-bound parent.
- **Pass 1 (orphan epics, 3)**: rationalized in body — none are
  aggregator-shaped (decision-gated research card + 2 leaf-level
  GoC tooling cards).
- **Pass 2 (meta-fix rosters, 2)**: framework-summary wired with 3
  body-table siblings; snapshot-restore already had good roster
  coverage from Pass 3.

### Closure metric

| | Before | After |
|---|---|---|
| OPEN cards with edges | 36 / 116 (31%) | 65 / 116 (56%) |
| ALL cards with edges  | 53 / 333 (16%) | 88 / 333 (26%) |
| Net delta             | — | +29 cards |

### Empirical sort verification

Spot-check confirms GRPW amplification is now live: 6+ medium-
contribution isolates lifted from value=3.0 to 6.3 via 0.7 × 9.0
amplification through high-contribution doc-drift meta-fixes. Their
`value_path` traces are explicit and auditable (e.g. `benna-fusi-
2016-capacity-formula-not-in-cited-paper` → `paper-claim-vs-doc-
drift-meta-fix` → `self`).

Top-5 by value remain native-high (value=9.0); the lifts happen in
the medium tier where they should — making well-justified mediums
outrank isolated mediums. This is the sort behavior the v3 schema
was designed for; before this card, the amplification pathway was
structurally live but empirically dormant.

### Mindset audit

PASS — no biology axiom touched. This card was deck-graph editorial
only (frontmatter `advances`/`advanced_by` field updates; 3 body
notes for orphan-epic rationalization). No code, no docs, no
experiments. Same posture as parent card.

### Lessons captured

- **Explore agents will go beyond JSON-only when they have Bash.**
  Pass 3a's agent applied edges directly via `deck.py advance`. For
  this kind of mechanical editorial pass that's net helpful (saved
  one application step) but the prompt should call it out
  explicitly to prevent confusion. Pass 3c/3d's agents staying in
  JSON-only mode let me filter their inventions; mixed approach
  worked.
- **Agents invent target names when uncertain.** Pass 3c proposed
  sinks like `silent-state-corruption-meta-fix` that sound plausible
  but don't exist. Filter step (verify against actual deck) is
  non-negotiable. The cost of a fabricated edge is high — it would
  mask the absence of the real meta-fix card that should exist.
- **`epic` tag is overused as editorial grouping.** 3 of 5 open
  epics aren't aggregators; they're decision cards or leaf tooling
  work. Surface for `improve-deck`: consider distinguishing
  aggregator-epics from grouping-epics in the schema, or just stop
  applying the tag where it doesn't add structure.
