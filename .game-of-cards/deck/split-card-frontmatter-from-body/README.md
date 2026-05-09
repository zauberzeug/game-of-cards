---
title: split-card-frontmatter-from-body
summary: "Today every card lives at `.game-of-cards/deck/<title>/README.md` with YAML frontmatter fenced by `---` markers and a markdown body below. Proposal: move the frontmatter to its own file (e.g. `card.yaml`), leaving `README.md` as pure markdown. Trade-offs: smaller parser scope (no fence detection), GitHub renders the body cleanly without metadata noise, simpler grep for metadata across the deck — but it's a breaking change for every consumer repo's existing cards (one-shot mechanical migration), doubles per-card file count, and `goc show` UX needs to merge two files. Decision-gated because the answer reshapes work in `replace-pyyaml-with-vendored-parser`."
status: open
stage: null
contribution: medium
created: 2026-05-09
closed_at: null
human_gate: decision
advances: []
advanced_by: []
tags: [story, infra]
definition_of_done: |
  - [ ] Decision recorded on this card (vendor a migration tool vs. keep current shape).
  - [ ] If split: every existing card under `.game-of-cards/deck/` migrated by an idempotent `goc migrate-split-frontmatter` (or equivalent) command.
  - [ ] If split: `goc show <title>` renders the merged view (frontmatter file + body file) so the human-facing UX is unchanged.
  - [ ] If split: `parse_frontmatter` and `emit_frontmatter` are renamed / refactored to load/save a standalone YAML file; the fence-detection regex is removed.
  - [ ] If split: `replace-pyyaml-with-vendored-parser` body is updated to drop the "find the closing `---` fence" acceptance requirement.
  - [ ] If split: a minor version bump and a CHANGELOG / migration note ship together; consumer repos see a one-line `goc upgrade` instruction.
  - [ ] If stay: card is closed `disproved` with the reasoning recorded.
---

# split-card-frontmatter-from-body

## Status quo

Every card on disk is one file:

```
.game-of-cards/deck/<title>/
├── README.md       # frontmatter (YAML between ---) + markdown body
└── log.md          # closure / state-change history
```

`goc/engine.py:129` defines `FRONTMATTER_RE` to find the fenced
block. `parse_frontmatter` (L132) returns `(data, body)`. The
emitter at `emit_frontmatter` (L201) re-fences. So the read path
has a delimiter step; the write path has a delimiter step; the
parser has to know about markdown context.

## Proposal

Two files per card, no fences:

```
.game-of-cards/deck/<title>/
├── card.yaml       # pure YAML — frontmatter only
├── README.md       # pure markdown — body only
└── log.md          # unchanged
```

The engine's read path becomes "load YAML file → load body file";
no fence detection, no regex.

## Why now

This question is in scope **because** of
`replace-pyyaml-with-vendored-parser`. If we split before that
child ships, the vendored parser's acceptance set shrinks — no need
to handle `^---\n(.*?)\n---\n?(.*)$` line-counting against a
markdown context. The ~200 LOC parser drops a few percent of
complexity. If we don't split, the parser handles fenced
frontmatter as it does today.

## Pros

- **Smaller parser scope.** `replace-pyyaml-with-vendored-parser`
  doesn't need fence detection.
- **Clean GitHub rendering.** `README.md` becomes pure markdown;
  GitHub no longer has to strip the metadata block before rendering
  the body.
- **Simpler metadata grep.** `grep tags .game-of-cards/deck/*/card.yaml`
  is exact, no false positives from card bodies that mention `tags:`.
- **LLM scan efficiency.** An agent reading just metadata can `cat
  .game-of-cards/deck/*/card.yaml` without slurping kilobytes of
  body prose.
- **Format independence.** Splitting decouples metadata format
  from body format. Pairs naturally with
  `decide-card-body-format-readme-vs-html-vs-flexible`: if metadata
  always lives in `card.yaml`, the body file extension can vary
  per-project without complicating the parser.
- **Hand-edit safety.** Editing the body can never accidentally
  break the frontmatter (e.g. a stray `---` heading).

## Cons

- **Breaking change for every consumer repo.** Every existing
  card on disk needs migration. Tooling can do it idempotently
  (`goc migrate-split-frontmatter` or auto-migrate-on-load), but
  it's a one-shot disruption.
- **Twice the inodes per card.** Two files instead of one. Editor
  tabs, `find`, `git status`, all see twice as much.
- **`goc show` UX changes.** Currently dumps one file. With two,
  it has to merge them in the right order to preserve "this is
  the card."
- **Loses the static-site-frontmatter convention.** Hugo, Jekyll,
  Obsidian, Dataview etc. all use fenced frontmatter in the same
  file. A future static-site display tool for the deck (not
  currently a goal, but plausible) would need a custom adapter.
- **The card directory is no longer "drop in any markdown
  reader."** Today a curious user can read `README.md` in any
  editor and see frontmatter + body in one view. Split makes that
  two opens.

## Migration shape (if approved)

- New verb: `goc migrate-split-frontmatter` (idempotent — skip
  cards already split).
- Engine reads both shapes during a transition window: if
  `card.yaml` exists, use it; else fall back to fenced
  frontmatter in `README.md`. Single-version transition; remove
  fallback after one minor release.
- Templates under `goc/templates/game_of_cards/` switch to the
  new layout in lockstep.
- Existing `goc upgrade` runs migration automatically.

## Interaction with the runtime-deps epic

Should ideally be **decided before**
`replace-pyyaml-with-vendored-parser` enters implementation. If
decided "split" mid-implementation, the parser work has to be
revisited to drop fence detection. If decided "stay", the parser
work is unaffected.

## Decision needed

Split or stay. If split, also confirm the migration verb name and
the transition-window length (one release? two?).
