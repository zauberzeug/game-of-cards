---
title: goc-validate-accepts-a-card-body-that-carries-a-second-copy-of-the-frontmatter
summary: "A 2026-08-24 hygiene pass split a card at the text '## Decision required' inside its frontmatter DoD and wrote a stale second body plus a glued DoD fragment into the README; goc validate stayed green for two months. Add a validate warning for a body that repeats frontmatter keys or DoD checkbox lines outside code fences."
status: open
stage: null
contribution: medium
created: "2026-10-22T06:03:27Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — a scratch card whose body repeats a frontmatter key line (`definition_of_done: |`, `title:`) or a DoD checkbox line outside a code fence makes `goc validate` warn, and a card that shows such lines inside a fenced code block stays silent
  - [ ] TDD: the check runs over the whole deck without new warnings except true positives (this repo had exactly one, repaired in 7616adc2)
  - [ ] MECHANICAL: `Skill(refine-deck)` says to rewrite card sections through the engine's section helpers (or at least to split the body only, never the whole file text)
  - [ ] PROCESS: `uv run goc validate` passes and the suite is green
---

# goc validate accepts a card body that carries a second copy of the frontmatter

## Location

- `goc/engine.py` — `validate_card` checks parsed frontmatter values, never the body's structure.
- The damage: `.game-of-cards/deck/goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/README.md`, from the hygiene pass e8449764 (2026-08-24) until the repair in 7616adc2 (2026-10-22).

## What's broken

The 2026-08-24 hygiene pass rewrote that card's decision section to "a ratification". It located the section by the text `## Decision required` — whose first occurrence was not the body heading but the frontmatter DoD line `- [ ] EMPIRICAL: the chosen interpretation (see "## Decision required") is recorded in log.md…`. The rewrite therefore kept a new body, then a line starting `## Decision required") is recorded in log.md…`, the rest of the DoD, a `---` fence, and a full stale second copy of the old body (397 lines instead of 206). Every later hygiene pass, every `goc validate` run and every bot that read the card for two months saw nothing wrong: the frontmatter still parsed.

The engine's own section finder is line-anchored (`^## Decision required`, `goc/engine.py:671`) and would not have matched the DoD line — but it *would* match the glued fragment line, so the next `goc decide` would have spliced its decision into the garbage instead of the real section.

## Empirical evidence

A deck-wide scan on 2026-10-22 (`grep -c '^## Decision required")'` plus a count of `^---$` lines per README) found exactly one glued card; the other cards with extra `---` lines carry them legitimately inside code blocks (frontmatter-parser bug cards).

## Fix

A `goc validate` warning, e.g. `BODY_REPEATS_FRONTMATTER`, when the body — outside fenced code blocks — contains a line that is a frontmatter key of the schema (`^definition_of_done: \|`, `^title: `, `^human_gate: `), a DoD checkbox line with a method tag (`^  - \[[ x]\] (TDD|EMPIRICAL|MECHANICAL|PROCESS):`), or a second H1. Plus a sentence in `Skill(refine-deck)` that body rewrites go through the engine's section helpers.

Related: [parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/) (the same hygiene passes), [card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it](../card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it/).
