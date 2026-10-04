---
title: shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced
summary: "The shipped deck skill's layout block lists SCHEMA.md, README.md and deck.py as files in the deck directory, deck/reference.md calls deck.py the engine, and refine-deck tells agents to schedule a new tag as a SCHEMA.md PR. A fresh goc install creates none of these files: the schema ships inside the package, the CLI is goc, and project tags go in .game-of-cards/canonical-tags.md. The sentences are pre-package residue that install and every plugin payload copy into consuming repos."
status: open
stage: null
contribution: medium
created: "2026-10-04T07:03:17Z"
closed_at: null
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: reproduce.py exits zero — no skill installed by `goc install --local-skills` names `SCHEMA.md`, `deck.py` or a deck-root `README.md` the install does not create
  - [ ] MECHANICAL: the deck skill's layout block lists what a deck directory holds after install (the deck-level `log.md` and one directory per card); `deck/reference.md` names the `goc` engine; `refine-deck` Step 3 sends a new tag to the place `card-schema/reference.md` § Adding new tags names, by pointing at that section rather than restating it
  - [ ] TDD: a regression guard in `tests/` fails when any shipped skill template names `deck.py` or `SCHEMA.md`, and is fed the pre-fix lines verbatim to prove it fires
  - [ ] MECHANICAL: mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) and OpenClaw skills re-ported (`python3 scripts/port_skills_to_openclaw.py --check` green)
---

# Shipped skills still point at the deck script and schema file goc replaced

## Location

- `goc/templates/skills/deck/SKILL.md:102-112`, "The deck layout":
  ```
  deck/
    SCHEMA.md                 # canonical schema (frontmatter IS the schema)
    README.md                 # navigation + conventions
    deck.py                   # CLI; computes filtered views from frontmatter
    <title>/                   # one dir per card; never moves on state change
  ```
- `goc/templates/skills/deck/reference.md:57-58`: "Our cards are the rows;
  deck.py is the engine; the skills are the query interface."
- `goc/templates/skills/refine-deck/SKILL.md:236-240`, Step 3: "file via
  `Skill(create-card)` a card whose DoD is the SCHEMA.md PR adding the new
  tag + its predicate. Adding the tag itself remains a SCHEMA.md PR per the
  schema's "Adding new tags" rule".
- Copies regenerated from the templates: `.claude/skills/`, `.codex/skills/`,
  `claude-plugin/skills/`, `codex-plugin/skills/`, and the ported
  `openclaw-plugin/skills/`.

## What's broken

All three passages describe the deck as it was before goc became a package,
when a vendored `deck.py` script and a `SCHEMA.md` file sat inside the deck
directory. None of those files exists in a goc install:

- The engine is the `goc` CLI (`goc/engine.py`), not a `deck.py` in the deck.
- The schema ships inside the package as `goc/schema.yaml`, with a copy beside
  the card-schema skill. No `SCHEMA.md` is written anywhere.
- `goc install` writes no `README.md` in the deck directory. The project-level
  `README.md` sits one level up, in `.game-of-cards/`.
- A project adds tags in `.game-of-cards/canonical-tags.md`, under a
  `canonical_tags:` block that `goc validate` merges. `card-schema/reference.md`
  § Adding new tags says so; refine-deck restates that rule and names a file
  that does not exist.

The layout block also omits the one file the install does put in the deck
directory, the deck-level `log.md`.

The `deck/` root spelling in the layout block is a separate, decision-gated
question
([shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates](../shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates/)).
This card is about the files listed under that root, which are wrong under
either spelling.

## Empirical evidence

`uv run python .game-of-cards/deck/shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced/reproduce.py`
(2026-10-04) installs into a scratch git repo with
`goc install --agents claude --local-skills` and reads the installed skills:

```
goc install --agents claude --local-skills wrote 50 files.
  files named SCHEMA.md or deck.py among them: none
  .game-of-cards/deck/README.md exists: False
  .game-of-cards/deck/ holds: ['.goc-version', 'log.md']

6 installed skill line(s) name a file the install did not create:
  - .claude/skills/deck/SKILL.md:105: SCHEMA.md                 # canonical schema (frontmatter IS the schema)
  - .claude/skills/deck/SKILL.md:106: README.md                 # navigation + conventions
  - .claude/skills/deck/SKILL.md:107: deck.py                   # CLI; computes filtered views from frontmatter
  - .claude/skills/deck/reference.md:57: write-ahead logs happen invisibly. Our cards are the rows; deck.py
  - .claude/skills/refine-deck/SKILL.md:238: the SCHEMA.md PR adding the new tag + its predicate. Adding the
  - .claude/skills/refine-deck/SKILL.md:239: tag itself remains a SCHEMA.md PR per the schema's "Adding new
```

## Why it matters

The deck skill is the front door every consuming agent loads, and its layout
block is where a new reader learns what the deck directory contains. Two of
the three listed files are described as the schema and the CLI, so a reader
who goes looking for either finds nothing. The refine-deck sentence is the
sharper case, because an agent follows it: Step 3 tells it to file a card
"whose DoD is the SCHEMA.md PR", so the agent writes a closure contract for a
file that cannot be edited. It is the executed-rather-than-read rot shape that
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
tracks. The same pre-package residue was removed from the engine's module
docstring by
[engine-module-docstring-describes-pre-package-skill-layout](../engine-module-docstring-describes-pre-package-skill-layout/)
and from the installed project README by
[installed-files-point-readers-at-a-deck-folder-install-never-creates](../installed-files-point-readers-at-a-deck-folder-install-never-creates/).
Neither card reached these three passages.

## Fix

- `deck/SKILL.md` "The deck layout": drop the `SCHEMA.md`, `README.md` and
  `deck.py` lines and add the deck-level `log.md`. Keep the `<title>/` subtree,
  which is correct. Leave the root spelling to the abbreviation card's
  decision. `tests/test_skill_body_size.py` caps this skill at 10,100 bytes
  (10,094 used), so the net change must not grow it. Dropping three lines frees
  about 200 bytes.
- `deck/reference.md:57`: "deck.py is the engine" becomes "the `goc` CLI is the
  engine".
- `refine-deck/SKILL.md` Step 3: replace both "SCHEMA.md PR" mentions with a
  pointer to `Skill(card-schema)` `reference.md` § Adding new tags. That
  section names `.game-of-cards/canonical-tags.md` for project tags and the
  required `check` value for a new row. refine-deck is size-capped too, and
  sits at 14,198 of its 14,200 bytes, so the pointer must be no longer than the
  two sentences it replaces.
- Guard: no shipped skill template may name `deck.py` or `SCHEMA.md`. Feed it
  the pre-fix lines verbatim. `tests/test_skill_template_deck_links.py` already
  sweeps all six skill trees, and its docstring asks for new shapes to widen it
  rather than add a file.
- Re-sync the mirrors and re-port OpenClaw.

## Artifacts

- reproduce.py
