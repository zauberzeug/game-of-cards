---
title: card-skills-document-html-as-sibling-artifact-pattern
summary: "Two coupled decision cards resolve here (stay monolithic for frontmatter; keep README.md markdown). The `create-card` and `card-schema` skill bodies will document a new pattern: rich artifacts (HTML, SVG, interactive forms) live as sibling files in the card directory and are referenced from the README — same shape as `reproduce.py` for bug cards. No engine change, no new frontmatter field, no breaking migration; per-card opt-in for the ~10–20% of cards (decision matrices, state diagrams, decision-gate answer forms) that benefit from richness markdown can't express."
status: done
stage: null
contribution: medium
created: 2026-05-09
closed_at: 2026-05-09
human_gate: none
advances: []
advanced_by: []
tags: [story, documentation]
definition_of_done: |
  - [x] `create-card/SKILL.md` template documents the rich-artifact pattern (HTML / SVG / PNG / interactive forms as sibling files referenced from README.md)
  - [x] `card-schema/SKILL.md` template Layout section enumerates the optional rich-artifact files alongside `reproduce.py`
  - [x] Both edits mirrored byte-for-byte into `.claude/skills/` and `claude-plugin/skills/` (skill-parity tripwire passes)
  - [x] `goc validate` passes
  - [x] `split-card-frontmatter-from-body` closed `disproved` with the rationale recorded in its body and `log.md`
  - [x] `decide-card-body-format-readme-vs-html-vs-flexible` closed `disproved` with the rationale recorded, naming this card as the pattern's home
worker: {who: Rodja Trappe, where: main}
---

# card-skills-document-html-as-sibling-artifact-pattern

## Resolution context

Two decision cards converged here:

- `split-card-frontmatter-from-body` decided **stay monolithic**.
  The industry survey (13 systems, 11 use in-file frontmatter only;
  Jekyll explicitly rejected sidecars in
  [#1082](https://github.com/jekyll/jekyll/issues/1082)) and the
  quantified parser-savings (5 LOC out of ~250 in the planned
  yaml_lite parser) made the cost case for splitting the weakest of
  the proposal's six pros.
- `decide-card-body-format-readme-vs-html-vs-flexible` decided
  **keep markdown for `README.md`**, but the article's strongest
  cases (interactive forms for decision gates, colored diagrams,
  side-by-side comparisons) genuinely transfer for ~10–20% of cards.
  Rather than introduce a `body_format:` frontmatter field with
  renderer dispatch (extra moving part), use the card directory's
  existing bundle shape: rich artifacts live as **sibling files**
  alongside `README.md`, referenced from the README — the same
  pattern bug cards already use for `reproduce.py`.

## The pattern

A card directory may carry artifact files beyond `README.md` and
`log.md`. The README narrates the card; sibling files are concrete
artifacts the README points at. This already works for `reproduce.py`
on bug cards. Extending the pattern to rich visuals adds nothing to
the engine — it is a documentation change in two skills.

```
deck/<title>/
  README.md                       # narrative + links to artifacts below
  log.md
  reproduce.py                    # OPTIONAL — bug-class executable proof (existing)
  comparison-matrix.html          # OPTIONAL — colored option grid for a decision card
  state-diagram.svg               # OPTIONAL — vector diagram
  decision-form.html              # OPTIONAL — interactive answer form for human_gate: decision
  before-after-screenshot.png     # OPTIONAL — visual regression evidence
```

The README links to artifacts as `[See the comparison
matrix](comparison-matrix.html)`. GitHub renders the README inline;
clicking the link to a `.html` file shows source on github.com but
opens as a working page when viewed locally. For decision-gate cards
with interactive answer forms, the human opens the artifact in a
browser to fill it in.

## Why this beats a `body_format:` dispatch field

- **No engine change.** `goc show`, `goc validate`, `parse_frontmatter`,
  the planned `yaml_lite` parser — all stay identical. Sibling files
  are opaque to the engine.
- **No new schema field.** The card directory's "bundle of files"
  shape already exists; `reproduce.py` proved the pattern. The schema
  documents an existing convention rather than introducing a new one.
- **Per-card opt-in without per-project config.** A single decision
  card in a markdown-default repo ships `decision-form.html` without
  flipping a global flag.
- **GitHub inline rendering preserved for 100% of cards.** Artifact
  links degrade to "click to view raw" on github.com for the few
  cards that ship `.html` — same UX github.com gives any binary.
- **No coupling to the planned YAML parser.** The
  `replace-pyyaml-with-vendored-parser` work proceeds with its
  documented acceptance set; fence detection stays trivial.

## Skill changes

Two skill bodies need edits. Source of truth lives at
`goc/templates/skills/...`; per the project's plugin-asset
duplication contract, edits must mirror byte-for-byte into
`.claude/skills/...` and `claude-plugin/skills/...` so the
skill-parity tripwire (`validate_skill_dir_parity` in
`goc/engine.py`) passes.

1. `create-card/SKILL.md` — extend Step 5 ("write the body") with a
   sub-section on shipping rich artifact files when prose can't
   express the content. Distinct from the existing Step 6
   (`reproduce.py` for bug-class) — that's an executable proof; this
   is a presentation artifact.
2. `card-schema/SKILL.md` — extend the "Layout" code block to
   enumerate the optional rich-artifact files alongside
   `reproduce.py`. Make the bundle-of-files mental model explicit
   rather than implicit, so a future reader understands the card
   directory is the canonical extension point for richness.

No `decide-card` skill change: the pattern surfaces naturally through
`create-card` (which is invoked when a decision card is filed).

## Out of scope

- A renderer or viewer for `.html` artifacts inside `goc show`. The
  artifact-bundle pattern relies on the host OS / browser to render;
  goc's CLI surface stays text-only.
- Templates for common artifact shapes (decision matrices, state
  diagrams). Authors compose ad-hoc per card. If a recurring shape
  emerges later, file a follow-up card.