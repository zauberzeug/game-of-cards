---
title: decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting
summary: "A card's `## Decision required` options are authored in four mutually incompatible shapes (numbered-bold list, bold-run `**Option A —**` paragraphs, `### Option A` headings, and `###` sub-decisions that nest their own lists), with 22 distinct Pro/Con marker spellings and no schema field, validator, or shared parser declaring which is canonical. Every consumer that reads decisions programmatically hand-rolls a parser and drifts; two pointwise fixes have already shipped and closed. Blocks any batch-decide or triage surface that wants to present a card's own options faithfully."
status: open
stage: null
contribution: medium
created: "2026-07-26T13:59:47Z"
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [meta-fix, api-contract, documentation]
definition_of_done: |
  - [ ] PROCESS: decision recorded on which of the four option shapes is canonical, and whether nested sub-decisions are expressible at all (see `## Decision required`).
  - [ ] TDD: `reproduce.py` exits zero — exactly one shape carries selectable choices across the deck, and no card misparses under the canonical reader.
  - [ ] MECHANICAL: one shared decision reader lands in `goc/engine.py` (options, per-option rationale, Pro/Con, recommended marker) and is the only implementation any consumer calls.
  - [ ] MECHANICAL: `goc/schema.yaml` documents the canonical option shape as part of the decision-gate contract.
  - [ ] TDD: a regression test asserts the reader's output for one card of each legacy shape, so a future shape change fails the build instead of silently reshaping output.
  - [ ] MECHANICAL: `goc validate` warns (advisory, not gating) on a `human_gate: decision` card whose section exposes no parseable option list — today 10 such cards exist.
  - [ ] PROCESS: `Skill(card-schema)` § "Decision-gate contract" and `Skill(create-card)` Step 3 state the canonical shape so newly authored cards conform.
  - [ ] PROCESS: the four instance cards named under "Why it matters" are cross-referenced or edge-wired to this card, per whichever the shape decision picks.
---

# `## Decision required` options have no machine-readable shape, so every reader reimplements a parser

## Location

- `goc/schema.yaml` — declares `human_gate` and its enum, but nothing about the
  body contract a `decision` gate implies.
- `goc/engine.py` — `DECISION_REQUIRED_RE`, `RESOLVED_DECISION_RE`,
  `replace_or_append_decision`, `validate_decision_verdict_coherence`: four
  independent readers of the decision section, none of which reads the *options*.
- `.claude/skills/card-schema/SKILL.md` § "Decision-gate contract" — requires the
  section, specifies no shape for its contents.
- `.claude/skills/decide-card/SKILL.md` — bridges the options to
  `AskUserQuestion` by asking the agent to read them by eye.

## What's broken

The decision-gate contract mandates the *section* and says nothing about the
*options inside it*. `card-schema` requires only that the section exist:

> When `human_gate: decision`, the body MUST carry a `## Decision required`
> section enumerating the credible options.

"Enumerating" is unconstrained, so 137 gated cards have enumerated four
different ways — all valid Markdown, all valid GoC, mutually unparseable:

```markdown
1. **`exit 2 + ERROR`** — strict, mirrors `cannot advance a card with itself`.

**Option A — make the check itself dangling-aware.** Split the filter so …

### Option A — Register stub subparsers on `_build_parser` (recommended)
- **Pro:** smallest change; help text stays consistent.

### The three candidate shapes (DoD item 1)
1. **Strict-refuse** — print `goc: error: <reason>` to stderr, `sys.exit(2)`.
```

The fourth is the dangerous one: an `###` sub-decision that nests its own
numbered list. A reader that resolves `###` headings as options — the obvious
strategy, since the third shape puts options exactly there — reports the
*heading count*, not the card's options.

Pro/Con annotation is equally unconstrained: 22 distinct marker spellings
(`Pros:`, `**Pro:**`, `- Con —`, `Trade-off:`, and inline mid-paragraph
`… behaviour. Cons: requires a sweep …`), so a reader that splits on
line-leading markers silently glues a Con onto the preceding Pro. Likewise
`recommended` appears in three unrelated places: a `(recommended)` label suffix,
a separate `### Recommended default: X` heading, and bare prose.

Two pointwise fixes have already shipped **and closed** against this same root,
each teaching one reader one variant:

- [decide-card-rephrases-and-reorders-the-cards-own-options](../decide-card-rephrases-and-reorders-the-cards-own-options/)
  (closed 2026-05-26) — told `Skill(decide-card)` to preserve source labels and
  order when bridging to `AskUserQuestion`. Guidance to a human-facing consumer;
  no structure for a programmatic one.
- [decision-verdict-coherence-check-skips-rubric-derived-decision-headings](../decision-verdict-coherence-check-skips-rubric-derived-decision-headings/)
  (closed 2026-06-15) — widened `RESOLVED_DECISION_RE` for one heading variant.

That is the `meta-fix` signature this repo already acts on elsewhere: two
independent pointwise repairs to hand-rolled copies of the same missing
abstraction.

## Empirical evidence

`uv run python .game-of-cards/deck/decision-required-options-have-no-machine-readable-shape-and-parsers-keep-drifting/reproduce.py`:

```
gated cards with a '## Decision required' section : 137

authored option shapes found (all in one deck):
    98  numbered-bold-list
    12  bold-run-option-paragraphs
    11  h3-option-headings
    10  no-parseable-list
     6  h3-subsections

distinct Pro/Con marker spellings: 22
    19  'con'
    16  'Pros:'
    13  'pro'
    12  'Cons:'
    11  '**Pro:'
     8  'cons'
     8  '**Con:'
     7  'Trade-off:'

concrete misparse — H3 reader vs the card's real option list:
  audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings
     sub-decision '1. Trigger condition — when does audit-deck *extend* vs. file fresh?'
     H3 reader sees 3 option(s); the card offers 4
  audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings
     sub-decision '2. Append mechanism — engine verb vs. body edit'
     H3 reader sees 3 option(s); the card offers 2
  audit-deck-cannot-extend-an-existing-umbrella-card-for-related-findings
     sub-decision '3. Closure semantics — when does an umbrella close?'
     H3 reader sees 3 option(s); the card offers 3
  mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success
     sub-decision 'The three candidate shapes (DoD item 1)'
     H3 reader sees 2 option(s); the card offers 3

VERDICT: 4 mutually incompatible option shapes carry selectable choices;
         10 gated cards expose no parseable list at all.
         No schema field, validator, or shared parser declares which is canonical,
         so every reader hand-rolls its own and drifts.

reproduce: FAIL (defect stands)
```

Exit 1.

## Why it matters

With 144 of 164 open cards sitting at `human_gate: decision`, the parked-card
pile is the deck's binding constraint, and any tool built to drain it must read
these options. The failure is not cosmetic: on
`mutation-verbs-accept-invalid-input-and-report-misleading-no-op-success` — the
keystone whose ruling settles eight siblings — an H3 reader presents its two
*sub-decision headings* as the choices and buries the three actual candidate
shapes (Strict-refuse / Exit-0-with-stderr-WARNING / Distinct no-op message)
inside one of them. A human handed that reads the wrong question, and a recorded
`goc decide` would carry a decision text the card never offered.

This card is the root; these are its known instances:

- [decide-misparses-fenced-double-hash-line-as-decision-section-terminator](../decide-misparses-fenced-double-hash-line-as-decision-section-terminator/)
  — the section *boundary* half of the same missing contract.
- [goc-decide-leaves-prior-decision-block-when-the-body-already-has-one](../goc-decide-leaves-prior-decision-block-when-the-body-already-has-one/)
  — `replace_or_append_decision` knows two body shapes and not the third.
- [decide-card-rephrases-and-reorders-the-cards-own-options](../decide-card-rephrases-and-reorders-the-cards-own-options/) (closed)
- [decision-verdict-coherence-check-skips-rubric-derived-decision-headings](../decision-verdict-coherence-check-skips-rubric-derived-decision-headings/) (closed)

Sibling in kind, different subject:
[dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting](../dod-fence-mask-reimplements-commonmark-fences-and-keeps-drifting/)
— the DoD half of "body content parsed by hand-rolled Markdown readers".

## Decision required

Three credible directions. All three end with one shared reader in the engine;
they differ in what they demand of the 137 cards already written.

1. **Declare one canonical prose shape and add an advisory validator.** Pick the
   numbered-bold list (98 of 137 cards, the de-facto majority), teach one engine
   reader that shape plus a tolerant fallback for the other three, and have
   `goc validate` warn on non-conforming gated cards without gating. Pros: no
   card rewrites, no schema change, immediate win for every consumer; the
   tolerant fallback keeps history readable. Cons: prose stays the source of
   truth, so a sufficiently creative author can still invent a fifth shape; the
   fallback is exactly the kind of multi-shape branch this card is trying to
   retire.

2. **Move options into frontmatter as a structured field.** Add an optional
   `decision_options:` list (label, rationale, pros, cons, recommended) that the
   body renders from. Pros: genuinely machine-readable, validatable, and
   diff-friendly; no Markdown parsing anywhere; nested sub-decisions become
   expressible as a real nested structure. Cons: the largest change on the
   board — it touches the schema, the emitter, `goc decide`, and every authoring
   skill, and it splits the decision across frontmatter and body, cutting against
   [split-card-frontmatter-from-body](../split-card-frontmatter-from-body/)'s
   disproved conclusion; 137 cards need migration or a permanent legacy path.

3. **Keep prose free-form; ship the reader as the contract.** Land one shared
   parser that handles all four shapes, test it against a fixture per shape, and
   declare *the reader* canonical rather than the syntax. Pros: zero authoring
   burden and zero migration; matches how the DoD fence mask is being handled.
   Cons: does not retire the class — the reader stays a four-branch heuristic
   that the next authored shape breaks, and nested sub-decisions remain
   ambiguous by construction.

A second, smaller question rides along regardless of the above: **are nested
sub-decisions legitimate?** Two cards currently pose several independent
questions under one `## Decision required`, which `goc decide` cannot express —
it records a single decision string per card. Either sub-decisions get a
first-class representation, or such cards should be split into siblings at filing
time. Recording that alongside the shape choice avoids a third pointwise fix.

## Fix

Deliberately not applied — the shape choice above changes what the fix is. Once
recorded, the mechanical work is a single reader in `goc/engine.py` returning
`(question, [options], recommendation)` with every existing decision-section
consumer routed through it, plus the schema and skill wording that makes the
choice discoverable to authors.
