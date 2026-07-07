# card-schema reference — deep dives

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the question at hand.

## Rationale

XP's **system metaphor** (Beck, 1999): a shared vocabulary that lets
humans and agents collaborate without re-deriving terms each
conversation. Names mean the same thing across every commit, every
sub-agent, every /loop iteration. Without that contract, frontmatter
rots into ad-hoc prose and the deck loses its read-pattern guarantee.

## What goes where — concrete consequences

- A new "Latest finding (DATE)" block at the bottom of the README is
  an antipattern — it accumulates contradicting versions of the
  truth. Rewrite the relevant README section in place; append the
  finding to `log.md` with the date.
- A state mutation that does not touch `log.md` (status flip,
  decision recorded, scope reframing) leaves a gap in the audit
  trail. Append the journal entry even when the README rewrite alone
  would "look complete".
- Decision-gate cards: keep the options matrix and `## Decision
  required` section current in the README; each round of
  consideration appends to `log.md`; the final resolution rewrites
  the dashboard.
- Closure does not freeze the card. Post-close amendments are valid
  appends to `log.md` (dated `Post-close amendment` entry with a
  forward reference) plus an optional one-line `> Later evidence: …`
  pointer atop the README when a cold reader would otherwise be
  misled. See `Skill(finish-card)` "After closure".

## Timestamps

Both `created` and `closed_at` accept two shapes:

- **ISO 8601 UTC datetime** — `YYYY-MM-DDTHH:MM:SSZ`. What `goc new`
  and `goc done` write, so multiple cards moved through the same day
  retain ordering.
- **Date-only** — `YYYY-MM-DD`. Legacy shape kept for backwards
  compatibility; pre-existing cards never get rewritten.

The two are deliberately ordering-compatible: lexicographic string
compare gives `"2026-05-10" < "2026-05-10T00:00:00Z" < "2026-05-11"`,
so sort keys, `--since` filters, and aging logic work uniformly
across a mixed deck. UTC only — local timezone offsets are rejected
because they break that ordering and make cross-machine analysis
ambiguous. Validator rule is symmetric: `closed_at` required iff
`status` is terminal, null otherwise.

## Draft contract

`draft` is a boolean overlay marking a card as an unauthored
scaffold — created but not yet written. Orthogonal to `status`: a
draft card is still `status: open`; `draft: true` says "not yet
real," the way a `waiting_on` overlay says "not yet workable."
Absent means authored (every card predating the flag is authored).

**Lifecycle:** `goc new` stamps it; it clears automatically on claim
or close (`goc status <title> active`, `goc done`), and explicitly
via `goc publish <title>` — which refuses on a pure placeholder
(nothing to publish until body and DoD are written).

**What the flag suppresses** — so unauthored work cannot be acted on
by automation (the dedup/supersede race that motivated it):

- Hidden from the default queue (`goc`, `goc next`, `card_is_ready`)
  and the scheduler; surfaced only under `goc --status all`, marked
  `✎` on the board.
- `goc status <title> {superseded,disproved}` refuses on a draft — a
  title-only placeholder must not be closed as a "duplicate."
- goc's auto-commit skips draft cards, so an unauthored scaffold
  never reaches shared state through goc. (An *external* auto-commit
  service bypasses goc and must filter drafts itself.)

A draft card may not be terminal: `goc validate` rejects
`draft: true` on a `done` / `disproved` / `superseded` card.

## Gate symmetry (decide ↔ close)

`goc decide` refuses on a card whose gate is already `none` (no
decision pending), and the four terminal-close paths (`goc done`,
`goc done --bundle`, `goc status <t> disproved`,
`goc status <t> superseded`) symmetrically refuse when
`human_gate != none`, telling the operator to run `goc decide`
first. The validator enforces the same invariant — terminal status
AND raised gate is a frontmatter contradiction — so a hand-edited
deck lands in CI, not in silence. Because of that, `goc decide`
doubles as the **repair** verb: it lowers a still-raised gate even on
an already-terminal card (recording the resolving decision, leaving
the card closed). The only terminal cards it touches are broken ones
— a cleanly closed card already carries `gate: none`.

## Decision-gate body contract

When any auto-agent sets `human_gate: decision`, the body MUST
contain a `## Decision required` section with:

1. **Reasoning** — one paragraph on *why* this needs human judgment
   (which axiom / literature / convention is in tension; what would
   be wrong about picking blindly).
2. **Options** — at least two named options (`Option A`, `Option B`,
   …), each with a one-line summary, **Pros**, **Cons**, and a
   concrete file:line preview of the edit (or "no code change;
   doc-only").
3. **Recommendation** — the agent's leaning, one line, with the
   dominant pro that drives it. Not binding.

`goc validate` accepts the card without it (the body is free-form),
but audit-deck / next-card treat a `decision` gate without the
section as a process bug.

A human resolves a `decision` card by reading the body, deciding, and
either editing the body to record the chosen option then dropping the
gate to `none`, or raising to `session` if the framing itself needs
an interactive revisit.

Autonomy ladder rationale: use `decision` / `session` **only** when
the unblocker is human judgement, stakeholder alignment,
prioritization, or a live discussion. If an agent can periodically
re-check the wait (upstream release, PR merge, dependency
publication) and proceed when the condition changes, the gate stays
`none` and the wait lives in the `waiting_on` overlay — a future
autonomous run observes the condition and clears it.

## Three-axis model (status / dependency-readiness / impediment overlay)

| Axis | What it answers | Where it lives | How it clears |
|---|---|---|---|
| **Progress status** | what is the card doing right now? | stored `status` | author flips it (`goc status`, `goc done`) |
| **Dependency readiness** | does an `advances` prereq still gate me from *starting*? | DERIVED from `advanced_by` predecessor status; ADVISORY ONLY | self-clears when the last prereq closes |
| **Impediment overlay** | is something exogenous stalling me? | stored `waiting_on` + optional `waiting_until` | `goc wait --clear`, or `waiting_until` elapses |

The three compose — a card may be `active` AND `waiting_on: external`
AND have an open prereq; each axis answers a different question.
(`human_gate` is a fourth axis with a different role: the Andon cord
telling agents NOT to autonomously claim.)

This decomposition replaces the legacy `status: blocked`. The
validator findings that policed the legacy value (`STALE_BLOCKED`,
`ORPHAN_BLOCKED`) are now migration aids — they identify cards still
encoded in the old style and recommend the axis-specific replacement
(drop to `open` for dependency-derived cases; set `waiting_on` for
exogenous waits). Nothing is ever steady-state `blocked`.

A card with an open `advances` prereq is still pullable — it surfaces
in `--ready` with an "awaiting: <prereqs> (you may start)" advisory
line. A genuine "must wait to start" is expressed explicitly via
`waiting_on`, NEVER inferred from a value-contribution edge that
cannot tell "must" from "should". An elapsed `waiting_until`
resurfaces the card regardless of `waiting_on` — the two waiting
signals are a single condition, not independent conjuncts.

## DoD layers

| Layer | Where it lives | Recorded by |
|---|---|---|
| 1 — card-specific | frontmatter `definition_of_done` | `goc done` (counts boxes) |
| 2 — project-wide | `.game-of-cards/config.yaml` `layer_2_project_dod` | `goc attest` (block in log.md) |
| 3 — GoC-wide | `.game-of-cards/config.yaml` `layer_3_goc_dod` | `goc attest` |

Layer 2 typically covers tests-pass / linting / project-defined
audits / no-debug / doc-consistency. Layer 3 covers schema-validates
/ advanced_by-closed / log.md-has-closure-entry / DoD-100%.
`Skill(finish-card)` Step 5 runs `goc attest <title>`, which appends
a `## Closure verification (DATE)` block to `log.md` listing each
check with pass/fail — six months later a reader sees *exactly* what
was verified at the moment of closure. Per the 2026-05-03 decision,
attest blocks closure on any automated/derived failure; no silent
waivers. (A fifth `SPIKE:` method-tag class for time-boxed
exploration is deliberately deferred.)

## Deck as scheduler vs record

The deck has two jobs and the relationship graph serves both. The
**scheduler axis** answers *what do I work on next?* — it walks edges
among live cards to compose priority (`compute_values`
Bellman-discounts the `advances` chain). The **record axis** answers
*how and why did we get here?* — it walks edges that include closed
cards so a cold reader can reconstruct the history of a decision
without parsing prose.

Consequence: **closed-card edges are first-class.** A card flipping
terminal does not discharge its relationship maintenance — its edges
remain load-bearing for the record axis. `goc validate` enforces
referential integrity for both axes regardless of either endpoint's
status; `compute_values` warns (rather than silently skips) when an
`advances` target cannot be resolved. Forensic reads do NOT fall back
to log.md prose for typed relationships — the typed link is the
contract; prose is the explanation.

**Why both typed and prose?** Recording a typed edge is O(1) at the
moment the relationship is known. Reconstructing a lost relationship
later from prose is O(read-everything) and lossy. For a methodology
whose readers are AI agents, a traversable typed graph beats
scattered per-card prose decisively, while the prose rationale
retains the *why* a graph edge can never capture.

## Value-chain rule

"X advances Y" is *defined* as "closing X delivers a piece of Y's
value chain," so a true edge ⇔ Y's value chain includes X ⇔ Y is
**not done** while X is open. There is no coherent "true edge you may
close past." Either the edge is true (the closure FAIL is correct),
or Y is genuinely closeable (the edge was false and points at the
wrong target — e.g. "more tests for C" does not advance C; it
advances *the testing of C's functionality*, a different card).

The `advanced-by-closed` derived check enforces this at closure time:
a card cannot move to `done` while any `advanced_by` member is
non-terminal. This is **correct, not over-strict**. The two honest
resolutions: wait for the upstream to close, or retract a false edge
with `goc unadvance <closing-title> --by <upstream-title>` — never
`goc attest --skip advanced-by-closed`, which leaves a dishonest edge
in the deck.

Decided in
[`advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose`](../../../.game-of-cards/deck/advanced-by-treated-as-hard-prerequisite-but-documented-as-mostly-loose/)
(Option E, 2026-05-26).

### Closure vs readiness — the asymmetry

The loose/strict distinction (~80% loose value contribution, ~20%
strict prerequisite — see
`rename-blocks-to-advances-and-design-value-sort`) governs **start
ordering, not closure**. A loose "X contributes; doesn't gate" edge
means you may *begin* Y before X is done; it does not mean Y can be
*declared done* with X's piece undelivered:

| edge | may Y *start* before X done? | may Y *close* while X open? |
|---|---|---|
| strict (X required before Y begins) | no (must wait — express as impediment overlay) | no |
| loose (X contributes, no order) | **yes** | **no** (X is in Y's value chain) |

The readiness predicate does NOT block on `advances` edges at all —
an `advances` edge is priority bias + closure gate + soft order
preference, not a "must wait to start". The strict case is an
*impediment*: express it on the dependent card via `waiting_on`; the
edge stays a pure value-flow + closure signal.

## Coordinating cards — aggregation epic vs governing cluster

Three shapes; only one uses edges:

1. **Aggregation epic** — its value chain *is* its children; closes
   *when they close*. Encoding: `child.advances: [epic]` (so
   `epic.advanced_by: [children]`). The `advanced-by-closed` check on
   the epic correctly holds it shut until the work lands.
2. **Governing cluster** — a decision or standard-setting card that
   closes *when the decision is made*, independent of the work it
   standardizes. Instances may exist before or after. Encoding: a
   **shared tag**, no `advances` edge in either direction (the
   `epic` tag predicate's "…OR carry the same epic-grouping tag" arm
   is exactly this tool).
3. **Backwards aggregation** — `epic.advances: [children]`. **The
   bug.** Two silent costs: (a) the value law is defeated — children
   no longer inherit the epic's value, so the priority sort can't see
   the chain; (b) every child trips a spurious `advanced-by-closed`
   FAIL because it reads as gated on a parent meant to outlive it. An
   autonomous worker halts on the whole cluster.

**Why an edge can't model a governing cluster.** An `advances` edge
encodes two hard, directional commitments at once: value flow AND
closure gating. For a soft, two-way govern relationship *both* are
wrong, so *either* edge direction mismodels it:

| encoding | what `advanced-by-closed` does | verdict |
|---|---|---|
| `decision.advances: [instances]` | blocks each **instance** behind the open decision | deadlock |
| `instance.advances: [decision]` | blocks the **decision** behind all instances | contradicts the decision's DoD |
| **shared tag**, no edge | nothing — pure grouping | **correct** |

**The tell:** a coordinator that is itself a *decision*
(`human_gate: decision`) or closes on its own deliverable is a
governing cluster → tag. Reach for an edge only when the
coordinator's closure genuinely waits on the work.

**Lint.** `goc validate` emits `BACKWARDS_EPIC_EDGE` (advisory) when
a card carries ≥ 2 `advances` entries whose contribution is
predominantly *lower* than its own. It names both candidate fixes
(flip vs convert-to-tag) — for a governing cluster the flip is also
wrong. The contribution-gradient heuristic keeps legitimate hubs
clean.

## Adding new tags

Project-specific tags (domain vocabulary, sub-project names,
cluster groupings) are added by the consuming repo via
`.game-of-cards/canonical-tags.md`:

```markdown
<!-- .game-of-cards/canonical-tags.md -->

```yaml
canonical_tags:
  - my-project-area
  - external-dependency
  - regulatory-review
```
```

`goc validate` reads this file from the consuming repo's root and
merges its `canonical_tags` list into the shipped enum. A
consuming-repo predicate table for the new tags is injected at the
end of the core skill's predicate table. Adding a new generic tag to
goc itself requires a PR against the `game-of-cards` repo — one tag
per PR for review hygiene.

## Worked example

```yaml
---
title: csv-export-button-truncates-rows-over-10000
summary: The CSV export endpoint silently caps output at 10000 rows when the underlying query returns more. No error, no warning header — large reports are missing data. Reproduces against the staging dataset.
status: open
stage: null
contribution: high
created: 2026-05-04
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract]
definition_of_done: |
  - [ ] reproduce.py exits non-zero (defect no longer fires)
  - [ ] export endpoint streams without row cap, or surfaces a 413 with documented limit
  - [ ] regression test added covering >10000-row exports
---

# Bug — CSV export silently truncates large datasets

(free-form markdown body explaining the defect, evidence, and fix
path; spawned-from / lineage notes go in log.md, not frontmatter)
```

Relationship-list YAML for a supersession:

```yaml
status: superseded
closed_at: 2026-05-14T10:00:00Z
superseded_by:
  - reframed-replacement-card
```

```yaml
# the successor:
supersedes:
  - the-old-card-it-replaces
```

The fields are optional and absent by default; they appear only when
a supersession is recorded. Non-empty edge lists render block-style:

```yaml
advances:
  - parent-epic-slug
  - another-dependency
advanced_by:
  - child-story-slug
tags: [story, api-contract]
```
