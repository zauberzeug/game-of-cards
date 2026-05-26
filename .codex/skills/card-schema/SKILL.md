---
name: card-schema
description: "Card schema reference — required/optional fields, status/stage/contribution/human_gate enums, canonical tags with predicates, DoD detection, relationship invariants, title naming convention. AUTO-INVOKE when other deck skills need schema context, or when user asks about field semantics, status lifecycle, DoD format, canonical tags, decision-gate body contract, or how to title a card. XP system metaphor — shared vocabulary makes the deck a contract, not a chat thread."
---

# Card Schema

XP's **system metaphor** (Beck, 1999): a shared vocabulary that lets
humans and agents collaborate without re-deriving terms each
conversation. Names mean the same thing across every commit, every
sub-agent, every /loop iteration. The schema is what makes the deck a
**contract** instead of a chat thread — every field has a defined
semantics, a defined enum, and a validator that refuses unknown values.
Without that contract, frontmatter rots into ad-hoc prose and the deck
loses its read-pattern guarantee.

This is the read-only reference. Mutations go through
`Skill(create-card)`, `Skill(advance-card)`, and `Skill(finish-card)`.
The authoritative schema lives in `Skill(card-schema)` frontmatter, which
`goc` parses with the same parser it uses for every card's
`README.md` — one parser, one mental model. The body of `Skill(card-schema)`
is a stub that points here; this file is the canonical explanation.

## Layout

```
deck/
  SCHEMA.md                 # frontmatter IS the schema; body points here
  README.md                 # navigation + conventions
  deck.py                   # CLI; computes filtered views from frontmatter
  <title>/                   # one dir per card; never moves on state change
    README.md               # frontmatter + dashboard body — latest knowledge + current state
    log.md                  # append-only journal — history, details, decisions, flow
    reproduce.py            # OPTIONAL — bug-class executable proof
    *.html / *.svg / *.png  # OPTIONAL — rich artifacts referenced from README.md
                            # (decision matrices, state diagrams, interactive
                            # answer forms, visual evidence — opaque to the engine)
    [other validation scripts]
```

The card directory is a **bundle of files**, not just `README.md`.
The README is the **dashboard**: a snapshot of the card's latest
knowledge and current state, rewritten in place as understanding
evolves so a cold reader sees only what is true now. `log.md` is
the **append-only journal**: history, details, decisions, and the
flow of how the card got here, preserved verbatim and never
rewritten. Sibling files are concrete artifacts the README references
— `reproduce.py` for executable proof on bug cards, `*.html` /
`*.svg` / `*.png` for visuals markdown can't express on decision
cards, visual-evidence cards, or interactive decision-gate forms.
The bundle pattern is the canonical extension point for richness
without introducing a new schema field, a body-format dispatch, or
any change to the engine; sibling files are opaque to
`parse_frontmatter`, `goc validate`, and `goc show`. See
`Skill(create-card)` Step 7 for the authoring contract.

Status changes mutate frontmatter, never directories. Cross-references
to `deck/<title>/` continue to work whether the card is open, active,
blocked, done, disproved, or superseded.

### What goes where (README dashboard vs `log.md` journal)

Two files, two edit disciplines:

| File | Role | Edit discipline | Reader semantics |
|---|---|---|---|
| `README.md` | **Dashboard** of latest knowledge and current state | Rewritten in place; outdated content is replaced, not amended below | A cold reader sees only what is true now |
| `log.md` | **Append-only journal** of history, details, decisions, and flow | Strictly appended; existing entries are never rewritten | A forensic reader can reconstruct how we got here |

Rule of thumb: **if a future reader would be misled by reading the
README in isolation, the dashboard needs the update; if the value is
in the sequence (when, by whom, why we changed our mind), the
journal needs the entry.** Most operations want both — rewrite the
README to reflect the new state, append a `log.md` entry that
records the transition.

Concrete consequences:
- A new "Latest finding (DATE)" block at the bottom of the README is
  an antipattern — it accumulates contradicting versions of the
  truth. Rewrite the relevant README section in place; append the
  finding to `log.md` with the date.
- A state mutation that does not touch `log.md` (status flip,
  decision recorded, scope reframing) leaves a gap in the audit
  trail. Append the journal entry even when the README rewrite
  alone would "look complete".
- Decision-gate cards: keep the options matrix and `## Decision
  required` section current in the README; each round of consideration
  appends to `log.md`; the final resolution rewrites the dashboard.
- Closure does not freeze the card. When new evidence surfaces after a
  card closes, the post-close amendment is a **valid append** to
  `log.md` (dated `Post-close amendment` entry, with a forward
  reference to the new card) and an **optional one-line pointer** at
  the top of the README body (`> Later evidence: …`) when the cold
  reader would otherwise be misled. Do not rewrite the closure entry
  itself; treat the amendment as additive. See `Skill(finish-card)`
  "After closure" for the cross-reference format.

## Status semantics

| value | meaning | what closes it |
|---|---|---|
| `open` | candidate for work; in the queue | promotion to `active`/`done`/`disproved`/`superseded` |
| `active` | work in progress (one author/agent at a time, by convention) | usually flips to `done` (or `blocked` mid-flight) |
| `blocked` | needs another card or external input; body should explain. Agent-checkable external conditions (upstream release, PR merge, dependency publication) keep `human_gate: none`; human-judgement blockers use `human_gate: decision\|session`. | unblocking; usually flips back to `active` |
| `done` | DoD checklist all ticked; `goc done <title>` enforces this | terminal |
| `disproved` | hypothesis investigated and ruled out; body documents the rebuttal | terminal |
| `superseded` | replaced by another card; replacement narrative in `log.md`; preserved for forensic continuity | terminal |

There is no separate `unverified` or `parked` state. Legacy
unverified-bug entries map to `status: open` + `tags: [unverified]`;
the promotion rule is "drop the `unverified` tag once a working
`reproduce.py` lands."

## Timestamps (`created`, `closed_at`)

`created` is stamped at card birth. `closed_at` is stamped on **every
terminal transition** — done, disproved, or superseded. `status` names
the outcome; `closed_at` is the single date per terminal exit, not a
shipped-only marker. Validator rule is symmetric: `closed_at` is
required iff `status` is terminal, null otherwise.

Both fields accept two shapes:

- **ISO 8601 UTC datetime** — `YYYY-MM-DDTHH:MM:SSZ` (e.g.
  `2026-05-11T14:30:00Z`). This is what `goc new` and `goc done` write
  going forward, so multiple cards moved through the same day retain
  ordering.
- **Date-only** — `YYYY-MM-DD` (e.g. `2026-05-10`). Legacy shape kept
  for backwards compatibility; pre-existing cards never get rewritten.

The two are deliberately ordering-compatible: lexicographic string
compare gives `"2026-05-10" < "2026-05-10T00:00:00Z" < "2026-05-11"`,
so sort keys, `--since` filters, and aging logic work uniformly across
a mixed deck. UTC only — local timezone offsets are rejected because
they break that ordering and make cross-machine analysis ambiguous.

## Summary (optional, but recommended)

`summary` is a free-form one-to-three-sentence description of the
card. It answers "what is this and why does it matter?" in scannable
form so triage views (`goc -v`) and the audit-deck / next-card
skills can prioritize without opening every body.

Guidelines:
- Keep it ≤ 3 sentences. If you need more, the body is the right place.
- State the *what* + *why*, not the fix path. The DoD already encodes
  closure.
- Plain prose. Avoid markdown formatting; the field renders inline.

The validator does not enforce sentence count — convention only.
Pre-2026-05-01 cards may have empty or absent `summary`; populate as
you touch them.

## Stage (KEP-style maturity, optional)

Most cards have `stage: null`. Use the alpha/beta/stable ladder only
for research items that progress through validation phases.

| value | meaning |
|---|---|
| `null` | no maturity tracking (defects, doc cleanups, mechanical tasks) |
| `alpha` | initial implementation, not yet validated |
| `beta`  | feedback gathered, secondary validation done |
| `stable` | production-ready, all graduation criteria met |

`status: done` + `stage: alpha` is valid: a research item's
alpha-phase work can be complete while beta/stable phases remain
ahead. Subsequent maturity work files a new card; if the new card
replaces the old, flip the old card to `status: superseded` and
record the replacement in its `log.md`. Use a shared epic tag or
`advanced_by` edge to express machine-readable dependency.

## Contribution scale

The per-card axis answering: **how much does closing this card
*alone* deliver or unlock for the project?** Type-agnostic — works
for bugs (load-bearing fix), features (user value), epics (terminal
milestone), refactors (downstream-enabling), docs (correction depth).

- `high`   — terminal milestone delivered (epic ships, demo unlock,
  public release) **OR** load-bearing infrastructure that many cards
  transitively depend on (framework derivation, foundational refactor,
  blocking-defect-in-shipping-path).
- `medium` — improves a working system (optimization, hardening,
  guard rail, test coverage of unstable area).
- `low`    — editorial polish (docs, stale references, tests for stable
  code, cleanup).

The `contribution` field declares atomic per-card value; the sort
algorithm composes it across the `advances` graph (with Bellman
discount γ=0.7) into a `value` score that drives `pull-card`. A
`tags: [docs]` `contribution: low` card is still worth fixing, but
a `contribution: high` framework defect outranks it — and a
`contribution: medium` card on a long chain to a `contribution: high`
sink can outrank an isolated `contribution: high` card via the
graph-amplified `value`.

## human_gate scale

`status` answers "what is the card doing right now?"
`human_gate` answers "does progress require a human?"

These axes are **orthogonal**. A card can be `blocked` with
`human_gate: none` (parked on an agent-observable external condition)
or `open` with `human_gate: decision` (queueable, but a human must
pick a direction before work proceeds). Setting `blocked` does not
automatically imply a human gate, and raising the gate does not
imply `blocked`.

Three-value autonomy ladder:

- `none`     — autonomous-loop-safe; cron may auto-pick. Examples:
  tolerance-creep test rename, stale-reference doc fix, mechanical
  sed-style replacement. Also covers `status: blocked` cards waiting
  on an external condition an agent can re-check (upstream release,
  PR merge, dependency publication, CI availability, scheduled
  research): the card is parked, but no human is needed to unblock —
  a future autonomous run can observe the condition and flip the
  card back to `open` or `active`.
- `decision` — needs ONE human go/no-go before work proceeds. Example:
  "Option A (rewrite the cite) vs Option B (rewrite the code)?" The
  body **must contain the framing already** — see "Decision-gate body
  contract" below — so the human can resolve asynchronously without
  re-deriving context.
- `session`  — needs interactive working session. Subsumes
  brainstorming/exploration cases. Example: research-impacting
  framework derivation; open architectural choice.

Use `decision` or `session` **only** when the unblocker is human
judgement, stakeholder alignment, prioritization, or a live
discussion. If an agent can periodically check the blocker and
proceed when the external condition changes, the gate stays `none`
even when the status is `blocked`.

Default for new cards created via `goc new`: `decision`.
Auto-agents (audit-deck, next-card reclassification) should pick a more
specific gate when the body content makes the choice clear (mechanical
→ `none`; research move → `session`).

Pickability rule (uniform across cron, /loop, and explicit-by-title
invocations):
- `none` → `Skill(next-card)` picks and proceeds.
- `decision` → `Skill(next-card)` does NOT pick; **session ends
  cleanly** with a one-line summary pointing at the parked card. The
  human reads the body's pre-recorded framing+options on their own
  time, picks a direction, drops the gate to `none` (or `session` if
  discussion is needed), then re-invokes `Skill(next-card)`. No idle
  agent waits.
- `session` → `Skill(next-card)` refuses to pick under autonomous
  mode; only an interactive session may advance, and only when the
  human explicitly confirms "yes, this is the working session for
  this topic."

### Decision-gate body contract

When any auto-agent sets `human_gate: decision`, the body MUST contain
a `## Decision required` section with:

1. **Reasoning** — one paragraph explaining *why* this needs human
   judgment (which axiom / literature / convention is in tension; what
   would be wrong about picking blindly).
2. **Options** — at least two named options (`Option A`, `Option B`,
   …). Each option:
   - One-line summary of the change.
   - **Pros** — bulleted list of what this option preserves /
     improves.
   - **Cons** — bulleted list of what this option costs / breaks.
   - Concrete file:line preview of the edit (or "no code change;
     doc-only").
3. **Recommendation** — the agent's leaning, one line, with the
   dominant pro that drives it. Not binding; the human can override.

Without this section, `goc validate` accepts the card (the body is
free-form), but the convention is enforced by the audit-deck /
next-card skills: a `decision` gate without a `Decision required`
section is a process bug, not a valid filing.

A human picking up a `decision` card resolves it by reading the body,
deciding, and either:
- Editing the body to record the chosen option (delete the unchosen
  ones, leave a one-line trail), then dropping the gate to `none` so
  `Skill(next-card)` can proceed mechanically; OR
- Setting the gate to `session` if the framing itself needs to be
  revisited interactively.

## Definition of Done (DoD) — three implicit layers

Scrum's **Definition of Done** as a machine-checkable closure
contract. The frontmatter `definition_of_done` field is **layer 1**:
the *card-specific* contract. Two more layers also apply at every
closure but live elsewhere:

| Layer | Where it lives | Visible at closure | Recorded by |
|---|---|---|---|
| 1 — card-specific | frontmatter `definition_of_done` | ✓ ticked boxes in README | `goc done` (counts boxes) |
| 2 — project-wide | `.game-of-cards/config.yaml` `layer_2_project_dod` (extracted from CLAUDE.md prose) | ✓ since 2026-05-03 | `goc attest` (writes block to log.md) |
| 3 — GoC-wide | `.game-of-cards/config.yaml` `layer_3_goc_dod` (universal across installations) | ✓ since 2026-05-03 | `goc attest` |

Layer 2 typically covers tests-pass / linting / project-defined
audits (e.g. closure-criteria audits per
`.game-of-cards/hooks/finish-card.md`) / no-debug /
doc-consistency. Layer 3 covers schema-validates /
advanced_by-closed / log.md-has-closure-entry / DoD-100%.

`Skill(finish-card)` Step 5 runs `goc attest <title>` which appends
a `## Closure verification (YYYY-MM-DD)` block to `log.md` listing
each layer-2 + layer-3 check with pass/fail. Six months from now,
a reader can see *exactly* what was checked at the moment of closure
— not just that the checkboxes were ticked.

Per the 2026-05-03 closure-failure decision, `attest` blocks closure
on any automated/derived failure. No silent waivers.

### Layer-1 format

Either:

- **Checkbox list (preferred):** `- [ ]` items that mutate to `- [x]`
  as criteria are met. `goc done <title>` requires every box to be
  `- [x]`.
- **Free-form prose:** allowed when checkboxes are awkward.
  `goc done` with prose DoDs requires explicit `--force` to bypass
  enforcement.

DoD detection: the CLI parses the field text for `^- \[[ x]\]` lines.
Zero matches → free-form prose. Otherwise → checkbox mode.

## Relationship fields

The kanban tracks two structured relationship axes in frontmatter,
**both bidirectional with consistency invariants**. Edges are stored
on both endpoints so triage views can traverse in either direction
without scanning, and so a half-written edge surfaces as a validator
error rather than silent rot.

### Deck as scheduler vs deck as record

The deck has two jobs and the relationship graph serves both. The
**scheduler axis** answers *what do I work on next?* — it walks edges
among live cards to compose priority (`compute_values` Bellman-discounts
the `advances` chain). The **record axis** answers *how and why did we
get here?* — it walks edges that include closed cards so a cold reader
(human or LLM) can reconstruct the history of a decision without
parsing prose.

A consequence: **closed-card edges are first-class members of the
deck graph.** A card flipping to `done` / `disproved` / `superseded`
does not discharge its relationship maintenance — its edges remain
load-bearing for the record axis. `goc validate` enforces
referential integrity for both axes regardless of either endpoint's
status; `compute_values` warns (rather than silently skips) when an
`advances` target cannot be resolved, so edge rot is loud, not
silent. Forensic reads do NOT fall back to log.md prose for typed
relationships — the typed link is the contract; prose is the
explanation.

### Value-flow axis (advances graph)

- `advances`    — list of slugs whose progress this card contributes to.
  "X advances Y" means closing X delivers a piece of Y's value chain.
  Reads correctly for the loose case (a test contributes to a feature
  shipping) and the strict case (a fix is required before its test
  can run) — both subsumed by "advance."
- `advanced_by` — list of slugs that contribute to this card's
  closure. Inverse of `advances`.

**Invariant:** if `A.advances` contains `B`, then `B.advanced_by` MUST
contain `A`. The validator reports any half-edge. The `goc advance
<title> --by <other>` and `goc unadvance <title> --by <other>`
commands maintain both sides atomically.

**Value-chain rule (the closure semantics).** Because "X advances Y"
is *defined* as "closing X delivers a piece of Y's value chain," it
follows that a true edge ⇔ Y's value chain includes X ⇔ Y is **not
done** while X is open. There is no coherent "true edge you may close
past." Either the edge is true (so Y isn't done — the closure FAIL is
correct), or Y is genuinely closeable (so the edge was false and
points at the wrong target — e.g. "more tests for C" does not advance
C; it advances *the testing of C's functionality*, a different card).

The `advanced-by-closed` derived check in `layer_3_goc_dod` enforces
this rule at closure time: a card cannot move to `done` while any
card in its `advanced_by` is non-terminal. This is **correct, not
over-strict** — the gate is the value-chain identity above. The two
honest resolutions when the gate fires are:

1. **Wait** for the upstream contributor(s) to close.
2. **Retract a false edge** with
   `goc unadvance <closing-title> --by <upstream-title>` — honest graph
   maintenance, not a bypass. Prefer this to `goc attest --skip
   advanced-by-closed`; the skip leaves a dishonest edge in the deck.

### Closure vs readiness — the asymmetry

The loose/strict distinction (~80% loose value contribution, ~20%
strict prerequisite — see
`rename-blocks-to-advances-and-design-value-sort`) is real, but it
governs **start ordering, not closure**. A loose "X contributes;
doesn't gate" edge means you may *begin* Y before X is done; it does
**not** mean Y can be *declared done* with X's piece undelivered. So
both loose and strict true edges block closure; they differ only on
whether work on Y may start first:

| edge | may Y *start* before X done? | may Y *close* while X open? |
|---|---|---|
| strict (X required before Y begins) | no | no |
| loose (X contributes, no order)     | **yes** | **no** (X is in Y's value chain) |

Consequence: the `advanced-by-closed` closure check correctly reads
all `advanced_by` as hard at closure time. The genuine over-read of
loose edges lives in *readiness* (the start-ordering question), which
is delegated to the sibling cards
`derive-dependency-readiness-…` (the start-ordering predicate) and
`add-waiting-overlay-…` (explicit human/external impediments), not
the closure gate.

**YAML format:** non-empty `advances` and `advanced_by` lists are
rendered as block-style (one `- item` per line). Empty lists use
inline `[]`. The `tags` field stays inline. Example:

```yaml
advances:
  - parent-epic-slug
  - another-dependency
advanced_by:
  - child-story-slug
tags: [story, api-contract]
```

Cycles are forbidden. A card advancing itself transitively is a
configuration error.

This axis subsumes hierarchy. An "epic" that aggregates sub-stories'
contributions is just the epic having `advanced_by: [story-1,
story-2, ...]`. A standalone derivative test that doesn't contribute
to any other closure has no value-flow edges — its provenance lives
in body / `log.md`, not frontmatter.

### Replacement axis (supersedes graph)

- `superseded_by` — list of slugs that replace this card. Set on the
  *old* card at the moment of supersession.
- `supersedes`    — list of slugs this card replaces. Set on the *new*
  card. Inverse of `superseded_by`.

A card cannot supersede itself or a non-superseded target;
`goc validate` enforces both rules. `goc status <title> superseded
--by <successor>` maintains both endpoints atomically — same atomicity
contract as `goc advance` / `goc unadvance` for the advances graph.
Prefer the CLI to manual edits.

**Invariants:**

- If `A.superseded_by` contains `B`, then `B.supersedes` MUST contain
  `A` (validator-enforced).
- A card with non-empty `superseded_by` MUST have `status: superseded`
  (validator-enforced).
- Every entry in `supersedes` MUST point at a card with
  `status: superseded` (validator-enforced).
- The replacement narrative still appends to `log.md` — the typed
  field is the *pointer* (machine-navigable), the journal entry is
  the *rationale* (different approach, scope split, reframing). Both,
  for different jobs.

**Why both typed and prose?** Recording a typed edge is O(1) at the
moment the relationship is known and cheapest to state. Reconstructing
a lost relationship later from prose is O(read-everything) and lossy —
inferring structure that was once explicit. For a methodology whose
readers are AI agents, a traversable typed graph beats scattered
per-card prose decisively, while the prose-rationale retains the
*why* a graph edge can never capture.

**YAML format** (same conventions as advances/advanced_by — block-style
when non-empty, inline `[]` when empty, fields absent on cards that
were never involved in a supersession):

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

The fields are optional and absent by default. They appear only when
a supersession is recorded.

### Grouping (use tags)

Use the `tags` field for grouping ("all the operating-amplitude
follow-ups", "all the literature-drift items", etc.). When a coherent
epic-shaped body of work emerges, add a canonical tag for it (one tag
per epic, retired when the epic closes). This keeps the schema flat —
no separate "epic / story / task" hierarchy to maintain.

### Lineage (forensic-only, not in frontmatter)

A card's "spawned from / grew out of" provenance lives in `log.md` as
free-form prose, not in frontmatter. Lineage doesn't drive triage and
rots quickly — the body / log is the right place for it.

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

(free-form markdown body explaining the defect, evidence, and fix path;
spawned-from / lineage notes go in log.md, not frontmatter)
```

## Title antipatterns (rejected at filing time)

Titles ARE the kanban label — a non-engineer reading `goc --board`
must understand what each card is about without opening the body.
`goc new` rejects titles matching any of these antipatterns:

| Pattern | Example | Why bad |
|---|---|---|
| `\br\d+\b` | `r88-csubstrate-replication` | Internal investigation-round reference; meaningless to a PO |
| `\bpath-\d+\b` | `path-2-recovery` | Sub-investigation step; not a deliverable noun |
| `\bphase-\d+\b` | `phase-1-stage-3` | Internal sequence reference |
| `\bbug-\d+\b` | `bug-140-fix` | Bug-tracker-style numbering (use the defect-shape clause instead) |
| `_md_` / `_py_` | `coupling-md-formula` / `agent-py-init` | Source-file infix; describe the *concept* not the *file* |
| camelCase tokens | `runSimulation-fails` | Function-name jargon; lower-kebab the intent |
| Math symbols (`Δ`, `≤`, `²`, `√`, `±`) | `late-hr-≥-0.5` | Use words (`gte`, `at-least`); the slug pattern allows `[a-z0-9-]` only |

When the regex fires, the CLI suggests an alternative phrasing
based on the *observable problem*, e.g. `r88-fix-attempt-3`
→ `csv-export-button-truncates-rows-over-10000`.

The Layer-2 quality pass (Sonnet-batched, in `Skill(refine-deck)
--quality-pass`) checks the same dimensions across the existing deck
and surfaces engineer-jargon titles for retitling via `goc move`.

## Adding new tags

The goc-shipped canonical-tag set is intentionally small. Project-
specific tags (domain vocabulary, demo / sub-project names,
literature-citation surfaces) are added by the consuming repo via
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
merges its `canonical_tags` list into the shipped enum. A consuming-
repo predicate table for these new tags can be appended to this skill
body via `!`cat .game-of-cards/canonical-tags.md`` injection at the
end of the predicate table below.

Adding a new generic tag to goc itself requires a PR against the
`game-of-cards` repo — one tag per PR for review hygiene.

## Tag application criteria

A tag is **load-bearing** for a card iff its predicate fires on the
card's title, H1 title, or first ~2500 chars of body. The criteria
below are conservative: when in doubt, drop the tag. Every applied tag
should give a future reader a useful filter; a tag that 70%+ of cards
carry filters nothing.

| tag | applies iff |
|---|---|
| `bug` | not `epic` and not `story` (default for findings) |
| `epic` | this card coordinates a coherent body of work; multiple other cards block it from closing OR carry the same epic-grouping tag (manually applied; conventionally one canonical-tag-per-epic, retired when the epic closes) |
| `story` | this card is part of an epic-grouping (manually applied; carries the same epic-grouping tag) |
| `unverified` | dir has no working `reproduce.py` AND was tagged at filing |
| `documentation` | finding's primary failure mode is doc-quality: title contains `doc` / `docstring` / `stale` / `drift` / `mismatch` / `cite` / `ambiguity` / `cross-doc` / `intra-doc` / `claim` / `framing` / `readme-`, or body cites `docstring`, `doc claim`, `doc-vs-`, `.md says/states/claims` |
| `test` | title starts `test-` or contains `tolerance` / `vacuous` / `regression`, or body cites `pytest`, `tests/`, `test_`, `assertion`, `tolerance creep` |
| `api-contract` | title or body cites a public API surface (a class, function, route, schema field that callers depend on) |
| `infra` | title or body touches infrastructure (`pre-commit`, `pyproject.toml`, `uv.lock`, `tooling`, CI workflows, packaging) |
| `meta-fix` | literal `meta-fix` / `family meta-fix` in title, title, or body |

Project-specific tag predicates appended below (consuming-repo authored):

!`cat .game-of-cards/canonical-tags.md 2>/dev/null || true`

These criteria are the v1 tag-application contract. New filings via
`goc new <title> --tag X` should fire on the same predicates; the
migration's 2026-05-01 pruning pass applied this contract retroactively
to legacy entries.
