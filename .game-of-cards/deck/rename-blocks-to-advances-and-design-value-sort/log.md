# Log — rename-blocks-to-advances-and-design-value-sort

## 2026-05-03 — Filed

Spawned by user discussion on priority computation in the deck
(May 3, 2026). The conversation surfaced two distinct moves:

1. The `blocks` field's strict-prereq reading mis-cues filers and
   under-encodes value flow. Rename to `advances` to match how the
   field is actually used (~80% value contribution, 20% strict prereq).
2. Once the field is honest about meaning, the sort algorithm in
   `pull-card` / `next-card` / `scan-deck` can consume it as a
   value-chain graph rather than a dependency-only graph.

The user's specific direction: "the 'advances' one should also
'migrate/update' the value-chain dependencies (only direct ones, not
cross reference epics) for all open cards and further think about
how the 'value' can be computed (eg whether it's needed to formalize
'epics', len(advances) computation for sorting etc...)".

Three deliverables collapsed into one card because they're tightly
coupled (rename → migration → value computation must agree on
semantics). The value-computation design step is gated on human
decision (gate=session) before implementation.

Companion card filed for the orthogonal move:
[`finish-card-records-implicit-dod-attestation`](../finish-card-records-implicit-dod-attestation/).

## 2026-05-03 — Closed

Shipped in 4 commits + 1 worktree merge:

1. **ddfc5d9f** — `blocks`/`blocked_by` → `advances`/`advanced_by`
   rename. Schema bumped 2 → 3. 332 cards migrated mechanically;
   deck.py + 7 skill files + schema.yaml updated.
2. **bf747820** — `impact` → `contribution` rename. Per-card axis
   named for atomicity (linguistically encodes "part of a whole",
   distinguishes from compound `value`). 332 cards + deck.py + 6
   skill files.
3. **2084ac27** — GRPW value sort + `-v` VALUE/WHY visibility.
   Algorithm: `value(c) = max(rank(c), γ · max(value(d) for d in
   advances(c)))` with γ=0.7 and rank `{high:9, medium:3, low:1}`.
   Tiebreak: direct-advances count (ToC near-term flow), then age.
   Cycle defense via in_progress set. JSON exposes `value` +
   `value_path`. Verified on synthetic chains.
4. **928e3fb1** — Merged `worktree-pull-cards` autonomous branch.
   15 fix-card closures landed (traces.py, synaptic_scaling.py,
   tgc.py wake-gate fixes + regression tests + docs). Git's per-line
   auto-merge cleanly combined schema-rename diffs (main) with
   status-flip diffs (worktree).

**Mindset audit**: PASS — no biology axiom touched (GoC methodology
evolution; tooling change orthogonal to phasor-agents framework).

**Design decisions made along the way:**
- Per-card axis named `contribution` (not `worth`/`stake`/`payoff`/
  `leverage`) because it's the only candidate that linguistically
  encodes atomicity by definition. Pairs cleanly with computed
  `value`.
- `impact` definition reframed from defect-anchored ("if wrong, every
  reader is affected") to value-anchored ("how much does closing this
  card alone deliver or unlock"). Type-agnostic across bugs/features/
  epics/refactors/docs.
- GRPW (Greatest Rank Positional Weight, RCPSP literature, Hartmann
  1999) chosen over direct-count or pure transitive count. γ=0.7
  Bellman discount handles the brittle-leaf problem (one critical
  leaf 12 hops away no longer dominates ancestors).
- Epics dropped as a structural primitive. The `epic` tag stays as
  editorial-only metadata. The graph + `contribution` field together
  encode value; an epic is just a high-contribution sink with no
  outgoing `advances`. No silent-typo failure mode (no special tag
  is structurally load-bearing).
- 3-tier contribution scale preserved (vs 5-tier from arXiv:2601.03444
  ICC research) to avoid migrating 332 cards' contribution values;
  expandable later.
- `-v` shows VALUE column at all verbosity levels + WHY trace at -v
  (only when amplified) so human/LLM readers can audit the sort.
  Addresses the industry concern (Linear, Jira deliberately don't
  auto-propagate priority because "opaque rank kills trust").

**Research grounding**: 3-agent parallel survey (PM frameworks,
graph-propagation literature, LLM-driven backlog tooling) executed
during the design conversation. Net synthesis: 3-tier coarse
contribution + GRPW with γ=0.7 + auditable WHY trace. Convergent with
OSS-bot consensus (Kubernetes Prow: priority + kind + size; Rust
triagebot: P-level + label + team).

**Follow-up filed**: [`populate-advances-graph-deeper-pass`](../populate-advances-graph-deeper-pass/)
for the editorial work of adding `advances` edges the old `blocks`
reading discouraged on the 279 graph-isolate cards. Without that,
the GRPW algorithm's amplification pathway is structurally live but
empirically dormant.
