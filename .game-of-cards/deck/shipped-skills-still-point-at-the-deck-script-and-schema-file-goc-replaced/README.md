---
title: shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced
summary: "The shipped deck skill's layout block listed SCHEMA.md, README.md and deck.py as files in the deck directory, deck/reference.md called deck.py the engine, and refine-deck told agents to schedule a new tag as a SCHEMA.md PR, all pre-package residue no goc install creates. The three passages now name what install writes and where tags go: the deck-level log.md, the goc CLI, and the card-schema section on adding tags. tests/test_skill_template_deck_links.py now bans both retired names from every shipped template tree and holds the layout block to a real install."
status: done
stage: null
contribution: medium
created: "2026-10-04T07:03:17Z"
closed_at: "2026-10-14T04:43:22Z"
human_gate: none
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [x] TDD: reproduce.py exits zero — no skill installed by `goc install --local-skills` names `SCHEMA.md`, `deck.py` or a deck-root `README.md` the install does not create
  - [x] MECHANICAL: the deck skill's layout block lists what a deck directory holds after install (the deck-level `log.md` and one directory per card); `deck/reference.md` names the `goc` engine; `refine-deck` Step 3 sends a new tag to the place `card-schema/reference.md` § Adding new tags names, by pointing at that section rather than restating it
  - [x] TDD: a regression guard in `tests/` fails when any shipped skill template names `deck.py` or `SCHEMA.md`, and is fed the pre-fix lines verbatim to prove it fires
  - [x] MECHANICAL: mirrors re-synced (`python scripts/sync_plugin_assets.py --check` green) and OpenClaw skills re-ported (`python3 scripts/port_skills_to_openclaw.py --check` green)
  - [x] TDD: every shipped deck skill's layout block is held to the deck directory a real `goc install` leaves behind (`DeckLayoutBlockTest`), and the check fires on the pre-fix block — the only guard that sees the phantom deck-root `README.md`, a name no ban can cover
worker: {who: "claude[bot]", where: main}
---

# Shipped skills still point at the deck script and schema file goc replaced

## What was broken

Three passages in the shipped skills described the deck as it was before goc
became a package, when a vendored `deck.py` script and a `SCHEMA.md` file sat
inside the deck directory:

- `goc/templates/skills/deck/SKILL.md`, "The deck layout", listed three files
  under the deck root that install never writes, and left out the one it does
  write, the deck-level `log.md`:
  ```
  deck/
    SCHEMA.md                 # canonical schema (frontmatter IS the schema)
    README.md                 # navigation + conventions
    deck.py                   # CLI; computes filtered views from frontmatter
    <title>/                   # one dir per card; never moves on state change
  ```
- `goc/templates/skills/deck/reference.md:57-58`: "Our cards are the rows;
  deck.py is the engine; the skills are the query interface."
- `goc/templates/skills/refine-deck/SKILL.md` Step 3: "file via
  `Skill(create-card)` a card whose DoD is the SCHEMA.md PR adding the new
  tag + its predicate. Adding the tag itself remains a SCHEMA.md PR per the
  schema's "Adding new tags" rule".

None of those files exists in a goc install. The engine is the `goc` CLI
(`goc/engine.py`). The schema ships inside the package as `goc/schema.yaml`,
with a copy beside the card-schema skill. `goc install` writes no `README.md`
in the deck directory; the project-level `README.md` sits one level up, in
`.game-of-cards/`. A project adds tags in `.game-of-cards/canonical-tags.md`,
under a `canonical_tags:` block that `goc validate` merges, as
`card-schema/reference.md` § Adding new tags says. Install and every plugin
payload copied the three passages into consuming repos, through
`.claude/skills/`, `.codex/skills/`, `claude-plugin/skills/`,
`codex-plugin/skills/` and the ported `openclaw-plugin/skills/`.

The `deck/` root spelling in the layout block is a separate, decision-gated
question
([shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates](../shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates/)).
This card fixed the files listed under that root, which were wrong under
either spelling, and left the root spelling alone.

## Why it matters

The deck skill is the front door every consuming agent loads, and its layout
block is where a new reader learns what the deck directory contains. Two of
the three listed files were described as the schema and the CLI, so a reader
who went looking for either found nothing. The refine-deck sentence was the
sharper case, because an agent follows it: Step 3 told it to file a card
"whose DoD is the SCHEMA.md PR", so the agent wrote a closure contract for a
file that cannot be edited. It is the executed-rather-than-read rot shape that
[doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
tracks. The same pre-package residue was removed from the engine's module
docstring by
[engine-module-docstring-describes-pre-package-skill-layout](../engine-module-docstring-describes-pre-package-skill-layout/)
and from the installed project README by
[installed-files-point-readers-at-a-deck-folder-install-never-creates](../installed-files-point-readers-at-a-deck-folder-install-never-creates/).
Neither card reached these three passages.

## What changed

- `deck/SKILL.md` "The deck layout" lists `log.md` (described the way install's
  own stub describes it: sprint notes, schema bumps) and the `<title>/`
  subtree, whose comment column is realigned. The skill went from 10,094 to
  9,965 bytes of its 10,100-byte cap.
- `deck/reference.md:57-58`: "the `goc` CLI is the engine".
- `refine-deck/SKILL.md` Step 3: the filed card's DoD "adds the new tag + its
  predicate per `Skill(card-schema)`'s `reference.md` § Adding new tags", and
  the pass never adds the tag itself. The pointer replaces both "SCHEMA.md PR"
  sentences without restating the section; the skill went from 14,198 to
  14,180 bytes of its 14,200-byte cap. The OpenClaw port reads "per the
  `card-schema` skill's `reference.md` § Adding new tags".
- Mirrors re-synced and OpenClaw re-ported.
- `tests/test_skill_template_deck_links.py`, widened as its docstring asks
  rather than joined by a new file, gained two checks:
  - `retired_files` bans `deck.py` and `SCHEMA.md` across the six skill trees
    and the four project-state template trees.
    `test_retired_file_predicate_flags_every_historical_offender` feeds it the
    five pre-fix lines verbatim.
  - `DeckLayoutBlockTest` runs a real `goc install --agents claude` into a
    scratch repo and requires every shipped deck skill's layout block to list
    exactly the visible entries install leaves in the deck directory, plus the
    `<title>/` placeholder. A name ban cannot see the third phantom entry, a
    deck-root `README.md`, because that name is legal for every card. Deriving
    the block from install catches it, and catches the next file install
    starts or stops writing there. The original DoD did not ask for this
    check; it is the fifth box.

## Evidence

`uv run python .game-of-cards/deck/shipped-skills-still-point-at-the-deck-script-and-schema-file-goc-replaced/reproduce.py`
installs into a scratch git repo with `goc install --agents claude --local-skills`
and reads the installed skills. Before the fix (2026-10-04) it exited 1:

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

After the fix (2026-10-14) it exits 0:

```
goc install --agents claude --local-skills wrote 50 files.
  files named SCHEMA.md or deck.py among them: none
  .game-of-cards/deck/README.md exists: False
  .game-of-cards/deck/ holds: ['.goc-version', 'log.md']

No installed skill names a file the install did not create.
```

The new test file, copied into a scratch worktree at the pre-fix commit
`00ecc037`, fails 7 times: the retired-name sweep with 30 hits (five lines in
each of six skill trees), and the layout check in all six trees, each block
parsing to `['SCHEMA.md', 'README.md', 'deck.py', '<title>/']` against the
installed `['<title>/', 'log.md']`. On the fix all 15 tests in the file pass.
The full suite passes (1308 tests), `goc validate` exits 0, and both
`sync_plugin_assets.py --check` and `port_skills_to_openclaw.py --check` are
green.

## Artifacts

- reproduce.py
