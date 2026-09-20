---
title: shipped-docs-abbreviate-the-deck-path-to-a-root-install-no-longer-creates
summary: "Shipped skill bodies write the card directory as `deck/<title>/` at 19 sites per skill tree, and `game_of_cards/config.yaml` does the same — but `goc install` creates the deck at `.game-of-cards/deck/<title>/` and never creates `deck/`. Most sites are prose a reader discounts, but several are executable instructions (`finish-card` says to run `uv run python deck/<title>/reproduce.py`), where an agent following the text literally in a consuming repo gets a file-not-found. Needs a call on whether to respell roughly 20 sites or keep the short form as a deliberate abbreviation."
status: open
stage: null
contribution: medium
created: "2026-09-20T04:43:35Z"
closed_at: null
human_gate: decision
advances:
  - doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] PROCESS: human picks option A (respell every site) or option B (keep the short form, fix only the executable sites); decision recorded in log.md.
  - [ ] MECHANICAL: the chosen edit landed across `goc/templates/skills/` and `goc/templates/game_of_cards/config.yaml`.
  - [ ] TDD: under option A, a guard pins the rule — no shipped template writes a bare `deck/` root — and is fed a historical site verbatim to prove it fires. Under option B, a guard pins the narrower rule that no *runnable* command in a skill body names a bare `deck/` path.
  - [ ] PROCESS: `python scripts/sync_plugin_assets.py --check` green, `python3 scripts/port_skills_to_openclaw.py --check` green, `uv run goc validate` clean.
---

# Shipped docs abbreviate the deck path to a root install no longer creates

## Location

- `goc/templates/skills/` — 19 sites per tree write `deck/<title>/...`. The
  executable ones:
  - `finish-card/SKILL.md:59` — ``Run `uv run python deck/<title>/reproduce.py` ``
  - `create-card/SKILL.md:204` — ``Run via `uv run python deck/<title>/reproduce.py` ``
  - `create-card/SKILL.md:185`, `audit-deck/SKILL.md:131,195` — tell the author
    to *write* `deck/<title>/reproduce.py`
- `goc/templates/game_of_cards/config.yaml:4` — ``records their results in
  `deck/<title>/log.md` ``
- Descriptive sites (`card-schema/SKILL.md:32` layout diagram,
  `deck/reference.md:19,32`, `advance-card/reference.md:52`,
  `finish-card/SKILL.md:68,101`, …) make up the rest.

## What's broken

`goc install` creates the deck at `.game-of-cards/deck/`. It never creates
`deck/` — the engine keeps a legacy `deck/` fallback for repos that predate
the move, but no fresh install produces one. Every site above therefore names
a path that does not exist in the repo the text was installed into.

For the descriptive sites this is a readability question. For the executable
ones it is a failure: an agent that follows `finish-card` literally runs
`uv run python deck/<title>/reproduce.py` and gets a file-not-found, in the
one place the skill is telling it to verify a fix before closing a card.

The shorthand is used *consistently*, which is why it is a convention call and
not a stale-reference patch. Its consistency is also what kept it invisible —
[`installed-files-point-readers-at-a-deck-folder-install-never-creates`](../installed-files-point-readers-at-a-deck-folder-install-never-creates/)
found it while sweeping for a different defect and deliberately scoped it out,
because the guard that card added has to keep `deck/<title>/` passing in order
to stay usable.

## Why it matters

This is the executed-rather-than-read rot shape
[`doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them`](../doc-accuracy-guards-are-opt-in-per-claim-and-new-doc-facts-keep-missing-them/)
names as its fourteenth instance: a skill body specifying a procedure an agent
follows literally. A wrong path in prose costs a reader a moment; a wrong path
in a command costs a closure verification.

## Decision required

Which spelling do the shipped docs use?

- **Option A — respell every site** to `.game-of-cards/deck/<title>/`. One
  rule, no reader has to know about the legacy root, and it is guardable by a
  flat "no shipped template writes a bare `deck/`" sweep. Cost: ~20 sites per
  tree times six trees (all mechanical, all auto-synced), and every line gets
  15 characters longer in docs already dense with paths.
- **Option B — keep the short form as a deliberate abbreviation**, and fix
  only the sites that are commands an agent runs. Cheapest, preserves
  readability, and matches how the docs already elide `.game-of-cards/` when
  talking about the deck conceptually. Cost: the rule becomes "short form in
  prose, full path in commands", which needs a narrower guard keyed on
  runnable lines and is easier to get wrong on the next edit.

Option B is the smaller change but the harder invariant to hold; option A is
the larger change but the one a guard can state in a sentence. Record the
choice and rationale in `log.md`, then the card becomes mechanical.

## Scope boundary

Not the same defect as
[`installed-files-point-readers-at-a-deck-folder-install-never-creates`](../installed-files-point-readers-at-a-deck-folder-install-never-creates/),
which was about citations naming a *concrete* card that no repo has. This card
is about the placeholder form itself. The two are deliberately pinned apart by
`test_card_path_predicate_leaves_the_placeholder_convention_alone` in
`tests/test_skill_template_deck_links.py`; whichever option is chosen here,
that test is the one to update.
