# create-card reference — edge cases and rationale

Companion to `SKILL.md`. Each section below is routed from the core
skill; read the one that matches the situation at hand.

## Rationale

XP's **story card as conversation** (Beck, 1999): a card is a
self-contained briefing for the next reader — human or agent —
written so the work can be picked up cold. Hallway context evaporates
between /loop iterations and conversational continuity is the first
casualty when a sub-agent reads the card three weeks later. Each card
must therefore carry its own evidence (verbatim quotes, reproducer
output), its own framing (what's broken, why it matters), and its own
closure contract (the DoD).

## Title quality

Beyond the mechanical antipattern guard, read the slug aloud and
avoid:

- **Word stuttering** — same root word repeated three or more times
  in one slug. Bad:
  `test-at-target-zero-delta-tautology-zero-times-anything-is-zero`
  (three "zero"s pile up; readers parse it twice). Good:
  `test-intrinsic-plasticity-at-target-passes-trivially` (same idea,
  parseable on first read).
- **Colloquial clauses as the back half** — "X-times-anything-is-Y"
  or "passes-because-Z-is-trivially-true" reads like a chat sentence,
  not a slug. The defect-shape clause should be a noun phrase a PO
  could read once. Use `passes-trivially`,
  `compares-identical-graphs`, `shadows-substrate-default` — not
  `is-trivially-zero-anyway`.
- **Family-shape mismatch** — when the card is the Nth instance of a
  known family, match the title shape of existing siblings. If R3 and
  R10 used `test-<name-fragment>-<defect-shape-clause>`, R11 in the
  same family must too. Inventing a new slug shape per instance makes
  the family illegible.

## Rubric-derived decisions (lazy Andon)

If the card being filed has a substantive decision at its core
(mechanism choice, sign convention, default anchored to a project
principle), consult the consuming repo's project-specific rubric —
injected into the core skill's Step 3 from
`.game-of-cards/hooks/create-card.md` — *before* picking
`--gate decision`.

If the rubric gives a clear answer with a principle citation AND
primary-source backing, scaffold the card with `--gate none` and
pre-write a `## Decision (rubric-derived)` body section recording:

- The choice (one line)
- The principle invoked (citation form prescribed by the hook)
- The primary-source citation (paper DOI/PMID, textbook chapter, or
  project-doc section)

The card joins the autonomous queue immediately; `pull-card`
implements without waiting on the human. Reserve `decision` /
`session` gates for questions the rubric cannot answer — resource
allocation, scope splits, taste calls, or missing primary-source
evidence.

This is the lazy Andon pattern: try the rubric, then pull. See
`Skill(decide-card)` "When an agent invokes this skill" for the full
agent-decision contract.

## Edge direction for coordinating cards (the three-way fork)

When the card being filed coordinates other work, decide which of
three shapes you're authoring before reaching for `--advances`. See
`Skill(card-schema)` "Coordinating cards" for the full value-law
reasoning; the operational form:

- **Aggregation epic** (its value chain *is* its children; closes
  when they close) → `child.advances: [epic]`. The child contributes
  upward; the epic aggregates downward via `advanced_by`. Concretely
  on a child filing: `goc new <child> --advances <epic> --commit`.
- **Governing cluster** (a decision or standard-setting card that
  closes when *decided*, independent of the cluster's work) → a
  **shared tag**, no `advances` edge in either direction. Add the tag
  via `--tag <epic-grouping-tag>` on both the governing card and its
  instances.
- **Never** `epic.advances: [children]` (backwards). It defeats the
  value law and trips a spurious `advanced-by-closed` FAIL on every
  child at attest time. `goc validate` emits a `BACKWARDS_EPIC_EDGE`
  advisory hint when this signature appears.

The tell: if the coordinating card itself has `--gate decision` or
otherwise closes on its own deliverable rather than on its cluster's
completion, it's a governing cluster → use a tag, not an edge.

## Draft contract

`goc new` stamps `draft: true`, so the fresh card is hidden from the
queue (`goc`, `goc next`) and protected from dedup/supersede
automation until it is authored. The flag clears automatically when
you claim the card (`goc status <title> active`, the usual next step)
or close it; release an authored-but-unclaimed card to the queue
explicitly with `goc publish <title>`. This closes the window where a
half-written scaffold could be superseded as a "duplicate" on its
title alone. See `Skill(card-schema)` "Draft" for the full contract.

## Reachability

For parser / emitter / serializer / storage-layer defects, the "Why
it matters" section must name the path that produces the offending
input — e.g. "the frontmatter emitter at `engine.py:NNN` writes this
string when a card has `closed_at: null`," or "a one-shot-authored
card supplied this header verbatim," or the concrete consumer flow
(`goc done → finish-card sync → ...`). Reachability is what separates
a real defect from a theoretical one; without it, a reader six months
later cannot tell whether the affected shape is actually produced in
shipping or only hypothetically possible.

## Rich artifact files

When the body benefits from content markdown can't express — colored
option grids, state-machine diagrams, side-by-side visual
comparisons, interactive answer forms for `human_gate: decision`
cards — ship the artifact as a sibling file in the card directory and
reference it from the body. Same bundle shape as `reproduce.py` for
bug cards; the engine treats sibling files as opaque and never parses
them.

```
deck/<title>/
  README.md                       # narrative + links to artifacts below
  log.md
  reproduce.py                    # OPTIONAL — bug-class executable proof
  comparison-matrix.html          # OPTIONAL — colored option grid
  state-diagram.svg               # OPTIONAL — vector diagram
  decision-form.html              # OPTIONAL — interactive answer form for a decision gate
  before-after-screenshot.png     # OPTIONAL — visual regression evidence
```

The README links artifacts as
`[See the comparison matrix](comparison-matrix.html)`. GitHub renders
the README inline; clicking a `.html` link shows source on github.com
but opens as a working page when viewed locally — identical UX
github.com gives any binary asset.

Use this pattern when:

- A decision card carries a colored options matrix that degrades to a
  wall of text in markdown.
- A `human_gate: decision` card ships an interactive form the human
  fills in (open the `.html` in a browser, fill it, paste the result
  back into the README's decision section).
- The card carries a state diagram, an `advances`-graph snapshot, or
  any visual that needs spatial layout markdown can't give.

Skip this pattern when prose alone communicates the content. The
default card stays single-file (`README.md` + `log.md`); rich
artifacts are an opt-in escape hatch, not a requirement. There is no
`body_format:` schema field and no engine dispatch — every artifact
is just another file in the card directory.
