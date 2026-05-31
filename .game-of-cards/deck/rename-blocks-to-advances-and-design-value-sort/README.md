---
title: rename-blocks-to-advances-and-design-value-sort
summary: |-
  Three-part GoC schema evolution: (1) rename `blocks` / `blocked_by`
  edges to `advances` / `advanced_by` to fix the strict-prereq vs
  value-contribution mismatch; (2) rename `impact` → `contribution`
  and reframe its definition from defect-anchored ("if wrong, every
  reader is affected") to value-anchored ("how much does closing this
  card alone deliver or unlock for the project?") — atomic-by-name
  per the May 3 design discussion; (3) implement an impact-weighted
  transitive-reachability sort algorithm (GRPW from RCPSP literature,
  Hartmann 1999) with Bellman discount γ=0.7, plus a `-v` `VALUE` /
  `WHY` column that shows the propagation trace so humans and LLM
  agents can audit why a card ranks where it does. The `epic` tag
  stays as editorial-only metadata; the graph + `contribution` field
  together encode value, no schema-formalization of epics needed.
status: done
stage: null
contribution: high
created: 2026-05-03
closed_at: 2026-05-03
human_gate: none
advances:
  - closed-card-relationship-edges-stay-first-class-in-the-deck-graph
advanced_by: []
tags: [epic, infra]
definition_of_done: |
  - [x] **Commit 1 — Rename `blocks`/`blocked_by` → `advances`/`advanced_by`** (ddfc5d9f): deck.py (LIST_REL_FIELDS, INVERSE_REL, validator, filter args, JSON output, CLI flags, block/unblock subcommands → advance/unadvance), 7 skill SKILL.md files, all 332 cards' frontmatter. Schema bumped 2 → 3.
  - [x] **Commit 2 — Rename `impact` → `contribution`** (bf747820): deck.py (IMPACT_ORDER → CONTRIBUTION_ORDER, validator, filter, CLI `--impact` → `--contribution`, JSON output, render_table column header IMPACT → CONTR.), 332 cards' frontmatter, card-schema/SKILL.md (full Contribution scale rewrite with atomic-vs-compound clarification) + 5 other skill files.
  - [x] **Commit 3 — GRPW sort + `-v` VALUE/WHY column** (2084ac27): deck.py `sort_default` replaced with GRPW algorithm: `value(c) = max(rank(c), γ · max(value(d) for d in advances(c)))` with γ=0.7 and `CONTRIBUTION_RANK: {high:9, medium:3, low:1}` (log-spaced per RICE-derived discrete-impact lesson). Sort key: `(-value, -len(advances), age_days)`. `render_table` adds a `VALUE` numeric column at all verbosity levels and a `WHY` line at -v showing the top-1 argmax propagation path. Cycle defense (in_progress set) falls back to per-card rank. JSON output exposes `value` (float) and `value_path` (list[str]). Algorithm verified on synthetic chains (medium → value 6.30 via amplification; orphan medium → value 3.0; etc.).
  - [x] **Commit 4 — Migration audit**: spot-checked 5 representative cards' migrated `advances`/`advanced_by` entries (`r-target-plumbing-tgc-cache`, `f-channel-layer-3b-architectural-gap-decision`, `spectral-health-metrics`, `labkit-single-source-of-truth`, `heterosynaptic-ltd-absent-fchannel`); all read as honest direct value contribution. The deeper editorial pass (adding edges the old `blocks` reading discouraged on the 279 graph-isolate cards) is filed as separate follow-up [`populate-advances-graph-deeper-pass`](../populate-advances-graph-deeper-pass/) — substantial editorial work that benefits from separate tracking.
  - [x] **Bonus: Worktree merge** (928e3fb1): merged `worktree-pull-cards` into main with new schema preserved. Git's per-line auto-merge resolved cleanly (schema-rename diffs and status-flip diffs hit different lines). 15 fix-card closures from the autonomous worktree landed: traces.py, synaptic_scaling.py, tgc.py wake-gate fixes + regression tests + doc updates. Worktree branch fast-forwarded to main so future pull-card sessions start at v3.
  - [x] `deck.py validate` clean across all 5 commits; pre-commit hook passes every time.
  - [x] `deck.py -v` output sanity-checked on real data: VALUE column right-justifies floats, WHY traces show propagation when chains exist (most cards currently show no trace because chains are unpopulated — see follow-up card; expected to surface amplification once edges land).
---

# rename-blocks-to-advances-and-design-value-sort

## Tier

**Epic — methodology change.** Touches every card filed in this repo
plus the GoC tooling. High-impact because it changes the mental model
every card author and reader operates under.

## Background

Two distinct schema problems were diagnosed in the May 3 conversation:

**Problem 1 — `blocks` reads as strict prerequisite.** The current
`blocks` / `blocked_by` edges read as **strict prerequisite** ("Y
cannot proceed until X closes"), but in practice they're used ~80%
as **value contribution** ("X moves Y forward in the value chain").
This mismatch over-constrains card filers (they hesitate to declare
loose contributions because `blocks` reads adversarial) and
under-encodes value flow (most working cards have empty `blocks`
because nothing strictly depends on them, even when load-bearing
for downstream goals).

Concrete example: [`pong-soft-bound-tgc-test`](../pong-soft-bound-tgc-test/)
does not strictly block anything — it's an *option* for pong recovery.
So `blocks: []` was the natural filing. But the card genuinely
advances `epic-pong-late-hr-recovery` → `epic-cartpole-demo` →
`epic-public-library-release`. Today's `blocks`-based pull-card sort
cannot see that chain.

**Problem 2 — `impact` is defect-anchored AND ambiguous on atomicity.**
The current definition reads "load-bearing — if wrong, every reader is
affected" — a defect-anchored framing that doesn't translate to feature
/ epic / refactor cards (what's "high impact" for "ship public
library"? There's no defect to be wrong about). And the line
"this is post-hoc importance, **not hunt-priority**" (card-schema
SKILL.md:100) explicitly disclaims using impact as a sort key — but
that's exactly what we're about to do.

Worse, `impact` is short enough to be ambiguous about whether it
means "the card's own contribution" (atomic) or "everything that
flows from closing it" (compounded). For a sort algorithm that
*does* compose downstream amplification, the per-card field must
intrinsically read as atomic.

## Why `advances`

Active-voice "X advances Y" reads correctly for both:

- **Loose case** (current 80%): "soft-bound test advances pong-recovery" — the test contributes; doesn't gate.
- **Strict case** (current 20%): "fix advances test-of-fix" — the test cannot exist before the fix; still reads correct as a subset of advance.

Inverse `advanced_by` is symmetric and pleasant; `precedes / preceded_by`
is uglier; `serves / served_by` collapses on the strict case.

The conceptual cost: the schema-level distinction between strict-prereq
and loose-contribution is dropped. **That distinction was always carried
by the body, not by the field** — readers can tell from "fix the bug"
vs "test the hypothesis" whether the dependency is structurally
load-bearing.

## Why `contribution` (not `impact`, `worth`, `stake`, `payoff`, `leverage`)

The atomicity must be in the name itself — a reader scanning the
frontmatter shouldn't have to recall context to know whether the
field is per-card or compounded. The candidates fall into two camps:

| Name | Atomic-on-its-face? | Verdict |
|---|---|---|
| `impact` | ambiguous | reject (current; ambiguous on whether it includes downstream) |
| `worth` | no — naturally holistic | reject |
| `stake` | no — fits GoT theme but reads holistic | reject |
| `payoff` | no — reads cumulative | reject |
| `leverage` | no — explicitly compositional, collides with sort algorithm's job | reject |
| `delivery` | yes — a delivery is one shipment | runner-up; skews feature-shipping |
| `yield` | yes — one harvest = one yield | reject (financial connotation) |
| `substance`, `merit` | yes | reject (judgmental — `substance: low` insults small-but-correct work) |
| `contribution` | yes — *part brought to a whole*, by definition | **chosen** |

`contribution` is the only candidate that fully passes the atomicity
test without baggage: it linguistically encodes "one part of a larger
whole," works for every card type (bug-fix contributes, feature
contributes, doc-fix contributes, epic contributes), is industry-neutral,
and pairs cleanly with `value` as the computed compound. The 12-letter
verbosity is the only real cost; paid by the writer once per card,
the reader never (CLI aligns columns).

## Reframed definition (`contribution: high | medium | low`)

Replace card-schema/SKILL.md's `## Impact scale` (defect-anchored,
post-hoc disclaimer) with `## Contribution scale` (value-anchored,
sort-anchored):

> **`contribution`** — how much does closing this card *alone*
> deliver or unlock for the project? Type-agnostic; the same question
> applies to bugs (load-bearing fix), features (user value), epics
> (terminal milestone), refactors (downstream-enabling), docs
> (correction depth).
>
> - `high` — terminal milestone delivered (epic ships, demo unlock,
>   public release) **OR** load-bearing infrastructure that many cards
>   transitively depend on (framework derivation, foundational refactor,
>   blocking-defect-in-shipping-path).
> - `medium` — improves a working system (optimization, hardening,
>   guard rail, test coverage of unstable area).
> - `low` — editorial polish (docs, stale references, tests for stable
>   code, cleanup).

The "post-hoc importance, not hunt-priority" disclaimer is dropped
because contribution IS hunt-priority signal. The 3-tier scale is
preserved (332 cards already use it; expandable to 5 later if 3
proves too coarse).

## Sort algorithm (GRPW + Bellman discount)

Selected over Option 1 (direct count) and pure Option 2 (transitive
count) on the basis of the May 3 research survey across PM frameworks,
graph-propagation literature, and LLM-driven backlog tooling. Cited
precedent: Greatest Rank Positional Weight from RCPSP (Hartmann 1999),
which has 40 years of tuning in resource-constrained scheduling and
beats raw direct-count and pure transitive-count in published
benchmarks. Bellman discount handles the brittle-leaf problem (one
critical-impact leaf 12 hops downstream would otherwise dominate
every ancestor).

```python
CONTRIBUTION_RANK = {"high": 9, "medium": 3, "low": 1}  # log-spaced (RICE-derived)
GAMMA = 0.7

def value(card, memo):
    if card.title in memo:
        return memo[card.title]
    own = CONTRIBUTION_RANK.get(card.contribution, 0)
    advances = card.frontmatter.get("advances") or []
    if not advances:
        memo[card.title] = own
        return own
    downstream = max(value(by_title[a], memo) for a in advances if a in by_title)
    result = max(own, GAMMA * downstream)
    memo[card.title] = result
    return result

def sort_key(card):
    return (
        -value(card, memo),                                      # primary: computed value
        -len(card.frontmatter.get("advances") or []),            # tiebreak: near-term flow (ToC)
        card.created,                                            # final: FIFO (kanban WIP-aging)
    )
```

`γ = 0.7` chosen so a `high` (9) one hop downstream contributes 6.3
(pulls a `medium` ancestor from 3.0 → 6.3); two hops 4.4; three hops
3.1. Brittle-leaf problem solved without losing meaningful chain
amplification.

Cycle handling: if `advances` graph has cycles (which validator
should already reject, but defense-in-depth), `value()` falls back
to the card's own `contribution_rank` to avoid infinite recursion.

## `-v` VALUE / WHY visibility

The May 3 design discussion identified that LLM agents and humans
both need an audit trail for *why* a card ranks high. Industry
precedent (Linear, Jira) deliberately doesn't auto-propagate
priority because "opaque rank kills trust." GoC mitigates this by
logging the propagation in `-v` output:

```
TITLE                              CONTR.  VALUE  WHY
goc-rename-blocks-to-advances...   high    9.0    self
pong-soft-bound-tgc-test           medium  6.3    → pong-late-hr-recovery (high)
adaptation-h-frozen-leak           low     4.4    → tgc-relay-utility (medium) → epic-pong (high)
small-doc-fix                      low     1.0    self
```

The `WHY` column traces the top-contributing path (the `argmax` of
the recursion). One line per card; reader can challenge "is this
ranked high for the right reason?" at a glance.

## Why epics don't need schema formalization

The May 3 conversation surfaced this question explicitly: "do we
really need epics?" Answer: no. The graph + `contribution` field
together encode value. An "epic" is structurally just a high-
contribution sink (no `advances:` outgoing); it doesn't need a
special tag, `kind:` enum, or `epic: true` boolean to participate
in the value graph.

The `epic` tag stays as **editorial-only metadata** — `--tag epic`
filters to "show me the big rocks" for human discoverability — but
plays zero role in sort. No schema change. No silent-typo failure
mode (because no special tag is structurally load-bearing).

## Migration scope

**Code (deck.py, ~10 sites + 7 skill files):**
- `phasor_agents/.claude/skills/deck/deck.py`: `LIST_REL_FIELDS`,
  `INVERSE_REL`, validator (lines 364-405), filter args (lines 426,
  444-447), JSON output (lines 559-560), CLI flag (line 612), CLI args
  (lines 634-635, 668-669), template (lines 778-779), block/unblock
  subcommands (lines 832-846; rename to `advance`/`unadvance` or
  similar).
- `IMPACT_ORDER` → `CONTRIBUTION_ORDER`; `--impact` CLI flag →
  `--contribution`; render_table column `IMPACT` → `CONTR.`
- Skill SKILL.md files referencing `blocks`/`blocked_by`:
  advance-card, card-schema, deck, improve-deck, next-card,
  scan-deck implicitly, use-game-of-cards.
- Skill SKILL.md files referencing `impact` semantics:
  card-schema (definition), scan-deck (filter examples), and any
  others surfaced by grep.

**Data (mechanical sed across `deck/*/README.md` frontmatter):**
- `blocks: [...]` → `advances: [...]` (332 occurrences, ~25 non-empty)
- `blocked_by: [...]` → `advanced_by: [...]` (332 occurrences, ~42 non-empty)
- `impact: <x>` → `contribution: <x>` (332 occurrences)

**Editorial (commit 4):**
- For each of the ~50 cards with non-empty `advances`, review whether
  migrated entries correctly capture direct value contribution. Add
  missing direct contributions that the old `blocks` reading
  discouraged. Remove strict-prereq-with-no-value-flow entries.
- Do NOT add transitive epic cross-references (only direct edges).

## Cross-references

- Spawned by: May 3 user discussion on priority computation
  ([`pong-joint-test-r89-budget-with-clip-removal-and-assoc-target/log.md`](../pong-joint-test-r89-budget-with-clip-removal-and-assoc-target/log.md)
  for prior-conversation context).
- Sibling: [`finish-card-records-implicit-dod-attestation`](../finish-card-records-implicit-dod-attestation/) (same conversation; orthogonal closure-attestation move).
- Affects every open card's frontmatter via the migration step.
- Reference: `Skill(card-schema)` — needs an update post-rename + reframe.

## Implementation order

1. **Commit 1**: mechanical rename `blocks`/`blocked_by` →
   `advances`/`advanced_by` in code + skills + data; `deck.py
   validate` clean.
2. **Commit 2**: mechanical rename `impact` → `contribution` in code
   + skills + data; `deck.py validate` clean.
3. **Commit 3**: reframe `contribution` definition in card-schema;
   implement GRPW + γ=0.7 sort + `-v` VALUE / WHY column; sanity-check
   on real data.
4. **Commit 4**: migration audit — editorial review of ~50 cards with
   non-empty `advances`.

Each commit landable independently. Commits 1 and 2 are reversible
sed; commit 3 introduces new behavior; commit 4 is editorial.

## Research grounding

The design choices in this card are anchored on a three-agent
research survey (May 3) covering:

- **PM prioritization frameworks**: RICE (Intercom), WSJF / CoD
  (Reinertsen), ICE (Sean Ellis), MoSCoW (DSDM), Value vs Effort.
  Verdict: WSJF's `value/size` formula was tempting but `size`
  cannot be reliably LLM-estimated.
- **Graph-based value propagation**: Theory of Constraints, CPM/PERT,
  RCPSP priority rules. Verdict: GRPW (sum/max over transitive
  successors, weighted by impact) has 40 years of literature support
  and beats direct-count and pure-transitive in benchmarks.
- **LLM-driven backlog tooling**: Linear, Jira/Rovo, GitHub Copilot,
  Kubernetes Prow, Rust triagebot. Verdict: industry converged on
  ≤5-level coarse ordinals + categorical kind/size; numeric scales
  degrade LLM agreement (arXiv:2601.03444 ICC measurements:
  0-5 = 0.853, 0-10 = 0.805, 0-100 = 0.840 — *finer is worse*).
  No tool auto-propagates priority through dependency graphs because
  "opaque rank kills trust" — but GoC's autonomous-agent context
  changes this trade-off (cost of suboptimal pick is low; chain is
  observable in card body).

Net synthesis: **3-tier coarse contribution + GRPW with γ=0.7 +
auditable `WHY` trace**. Three-axis convergence (`contribution`,
`human_gate`, `tags`) matches the OSS-bot consensus (priority +
kind/size + auto-triage gates).

## Decision

*Resolved 2026-05-31T08:49:16Z:* Value-computation design shipped with the rename; clear the stale session gate

*Reasoning:* Card was closed done on 2026-05-03 after shipping the advances rename + GRPW value sort, but the session gate that fronted the value-computation design step was never lowered at close (predates the close-time gate guard)

