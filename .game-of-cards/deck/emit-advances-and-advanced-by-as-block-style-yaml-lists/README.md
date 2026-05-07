---
title: emit-advances-and-advanced-by-as-block-style-yaml-lists
summary: "Switch the frontmatter emitter to render `advances` and `advanced_by` as YAML block-style lists (one item per line) instead of the current inline flow style (`[a, b, c]`). This eliminates the guaranteed merge conflict that today happens whenever two participants concurrently add a child card to the same parent epic — both end up rewriting the same single line. `tags` stays inline because it is short, stable, and rarely concurrent-edited. Includes a one-time migration of all existing cards' frontmatter so the new style is uniform across the deck."
status: open
stage: null
contribution: medium
created: 2026-05-07
closed_at: null
human_gate: none
advances:
  - support-multi-branch-and-multi-user-deck-workflows
advanced_by: []
tags: [story, infra, api-contract]
definition_of_done: |
  - [ ] `engine.emit_frontmatter` renders `advances` and `advanced_by` in YAML block-style (one `- item` per line) when the list is non-empty; empty lists still render as `advances: []` (single line, no false diff)
  - [ ] All other list fields (currently just `tags`) continue to render as inline flow-style — no change to today's `tags: [story, infra]` form
  - [ ] `engine.mutate_frontmatter_field` handles multi-line list fields: replacing `advances` or `advanced_by` updates the spanning block, not just one line. Mutators called from `goc advance` / `goc done` / etc. continue to work
  - [ ] `engine.parse_frontmatter` (already uses `yaml.safe_load`) requires no change — both styles parse to the same Python list. Verify by adding a test that round-trips a card from flow → block via the emitter
  - [ ] Schema example (`goc/schema.yaml`) updated to show block-style for `advances` / `advanced_by` so contributors copying the example get the new format
  - [ ] One-time migration script re-emits every card under `.game-of-cards/deck/` through the updated emitter, producing a single bulk commit. Diff is purely whitespace-equivalent for all fields except `advances` / `advanced_by`
  - [ ] `goc validate` passes after migration
  - [ ] Documented in CLAUDE.md / AGENTS.md so contributors editing frontmatter by hand know the convention (block for `advances` / `advanced_by`, inline for `tags`)
---

# Emit advances and advanced_by as block-style YAML lists

## Why

Today every list field in a card's frontmatter renders as a single
inline line:

```yaml
advanced_by: [a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q]
```

When two participants concurrently file a card that should advance
the same parent epic, both edits target the same line — git cannot
auto-merge "and" semantics on a single line, so a merge conflict is
guaranteed every time. As the multi-agent / multi-human workflow
becomes the primary use case (per
`support-multi-branch-and-multi-user-deck-workflows`), this collision
surface scales linearly with the number of active filers.

Block style turns each list element into its own line:

```yaml
advanced_by:
  - a
  - b
  - c
```

Adding an entry now extends the block by one line at a chosen
position; concurrent additions at different positions auto-merge.
PR diffs also become readable: a one-item change shows as `+1 line`
instead of a whole reformatted line.

`tags` stays inline because it is short (1-3 items), stable
(rarely changes after card creation), and almost never the locus
of a merge conflict. Keeping it inline preserves visual density in
the frontmatter where the cost-benefit doesn't justify block style.

## The non-trivial bit

`engine.mutate_frontmatter_field` (engine.py:146) is a
line-anchored regex replacement that explicitly assumes "every
field is one line" — see the docstring: "Avoids YAML round-trip
(which reorders keys and strips comments). Safe given the schema's
flat-YAML constraint — every field is one line."

Block-style lists violate that invariant for the affected fields.
The mutator needs to either:

1. Detect multi-line list fields and replace the whole spanning
   block (start at `^<field>:$`, end at the next `^<key>:` or
   `^---`), or
2. Use `ruamel.yaml` for these specific fields with round-trip
   preservation (heavier dependency).

Option 1 keeps the current dependency profile and is the natural
extension of the existing approach.

## Migration

A one-time pass that loads every card via `parse_frontmatter`,
re-emits via the updated `emit_frontmatter`, and writes back. Diff
is mechanical and large-but-uniform — one bulk commit, easy to
review at the level of "did the right two fields flip styles".

## Cross-references

- `support-multi-branch-and-multi-user-deck-workflows` — the
  parent direction this change directly serves
- `design-claim-protocol-with-branch-and-author-metadata` — also
  reduces concurrent-edit conflicts; complementary
- `make-autocommit-mandatory-when-deck-is-version-controlled` —
  raises the commit frequency, raising the conflict surface this
  card mitigates
