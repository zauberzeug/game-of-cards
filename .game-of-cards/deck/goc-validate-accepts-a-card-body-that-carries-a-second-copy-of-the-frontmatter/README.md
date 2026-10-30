---
title: goc-validate-accepts-a-card-body-that-carries-a-second-copy-of-the-frontmatter
summary: "A 2026-08-24 hygiene pass split a card at the text '## Decision required' inside its frontmatter DoD and left a DoD fragment, the `---` closer and a stale second body in the README, and goc validate stayed green for two months. goc validate now warns BODY_REPEATS_FRONTMATTER when a body, outside code fences, repeats a frontmatter key line, a DoD item at the block indent or its own H1. Its first deck run found two more cards (a body lost in May, an unfenced proposed DoD), both repaired, and Skill(refine-deck) now says to edit the body only."
status: done
stage: null
contribution: medium
created: "2026-10-22T06:03:27Z"
closed_at: "2026-10-30T05:05:36Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, meta-fix]
definition_of_done: |
  - [x] TDD: `reproduce.py` exits zero — a scratch card whose body repeats a frontmatter key line (`definition_of_done: |`, `title:`) or a DoD checkbox line outside a code fence makes `goc validate` warn, and a card that shows such lines inside a fenced code block stays silent — exits 0: both spliced scratch cards warn, the fenced one stays silent, `validate` exits 0. Against the pre-fix engine it exits 1. `tests/test_validate_body_repeats_frontmatter.py` pins each shape, the fenced and wrapped-prose negatives, and both damaged bodies as they sat on disk.
  - [x] TDD: the check runs over the whole deck without new warnings except true positives (this repo had exactly one, repaired in 7616adc2) — the first run over 823 cards flagged two more. One is `block-scalar-parser-collapses-whitespace-only-content-lines`, whose H1 and leading sections a re-emit dropped in 83c1408d; its body was restored from e1eb3ece. The other is `next-card-reclassify-checklist-cites-nonexistent-docs-framework-path`, whose proposed replacement DoD sat unfenced and is now fenced. The deck now draws no warning, and a live-deck test keeps it that way.
  - [x] MECHANICAL: `Skill(refine-deck)` says to rewrite card sections through the engine's section helpers (or at least to split the body only, never the whole file text) — the core says to edit the body only, splitting at the frontmatter closer and finding a section by its line-anchored heading. `reference.md` § Editing card bodies carries the incident, a split snippet and the repair recipe. Mirrors re-synced, OpenClaw port re-run.
  - [x] PROCESS: `uv run goc validate` passes and the suite is green — validate exits 0; 1444 tests OK.
worker: {who: "claude[bot]", where: main}
---

# goc validate accepts a card body that carries a second copy of the frontmatter

## Status

Fixed 2026-10-30. `goc validate` emits an advisory `BODY_REPEATS_FRONTMATTER`
warning for a card body that, outside fenced code blocks, repeats card text.
It looks for a frontmatter key line, a DoD item at the frontmatter's block
indent, or a repeat of the body's own H1. `Skill(refine-deck)` tells hygiene
passes to edit the body only. The check's first run over the deck found two
more cards, both repaired.

## Location

- `goc/engine.py` — `frontmatter_copy_lines` scans a body, and
  `validate_body_repeats_frontmatter` turns its hits into the warning. It is
  wired into `_cmd_validate` beside the other advisory classes.
- `goc/templates/skills/refine-deck/SKILL.md` (the intro, after the two action
  paths) and `reference.md` § Editing card bodies.
- `tests/test_validate_body_repeats_frontmatter.py`.
- The original damage: `.game-of-cards/deck/goc-waiting-filter-drifts-from-engine-on-elapsed-and-bare-waits/README.md`, from the hygiene pass e8449764 (2026-08-24) until the repair in 7616adc2 (2026-10-22).

## What was broken

The 2026-08-24 hygiene pass rewrote that card's decision section to "a ratification". It located the section by the text `## Decision required` — whose first occurrence was not the body heading but the frontmatter DoD line `- [ ] EMPIRICAL: the chosen interpretation (see "## Decision required") is recorded in log.md…`. The rewrite therefore kept a new body, then a line starting `## Decision required") is recorded in log.md…`, the rest of the DoD, a `---` fence, and a full stale second copy of the old body (397 lines instead of 206). Every later hygiene pass, every `goc validate` run and every bot that read the card for two months saw nothing wrong: the frontmatter still parsed.

The engine's own section finder is line-anchored (`DECISION_REQUIRED_RE`, `^## Decision required`, `goc/engine.py:680`) and would not have matched the DoD line — but it *would* match the glued fragment line, so the next `goc decide` would have spliced its decision into the garbage instead of the real section.

## Empirical evidence

The filing scan on 2026-10-22 (`grep -c '^## Decision required")'` plus a
count of `^---$` lines per README) found the one glued card. The new check, run
over all 823 cards on 2026-10-30, flagged two more:

- `block-scalar-parser-collapses-whitespace-only-content-lines` (done). It was
  filed without a frontmatter closer, so the engine read everything up to a
  `---` inside a pasted reproducer output as frontmatter, and the yaml-lite of
  that time accepted the prose. The `closed_at` re-quoting migration in
  83c1408d re-emitted the frontmatter from the parsed keys and dropped the H1
  and every section before the output. Today's parser refuses such a card with
  a parse error. The body was restored from the closure commit e1eb3ece.
- `next-card-reclassify-checklist-cites-nonexistent-docs-framework-path`
  (parked). Its "definition_of_done (replace after decision)" list was a
  deliberate copy, unfenced at the block indent. It is now fenced, with the
  content unchanged.

The scan also measured the rejected variants. A bare column-0 test over every
schema key adds two false positives from wrapped prose, lines opening
`status: **a card may be…` and ``waiting_until: 2099-01-01`). Assert…``. No
card body holds two H1s.

Against the pre-fix engine, `reproduce.py` exits 1 and the live-deck test
flags both cards above.

## Fix

`frontmatter_copy_lines` reports a body line, outside fenced code blocks
(`_dod_fenced_mask`, shared with the DoD scanners), in three cases:

- a key line that wrapped prose does not produce: `title:` or `human_gate:`
  followed by exactly one value token, or `definition_of_done:` followed by a
  block-scalar header. `status:` and `waiting_until:` are left out, per the
  measurement above.
- a DoD item at the two-space block indent `_emit_block_field` writes, with a
  method tag. A body's own checklist sits at column 0.
- an H1 that repeats the body's first H1: the head of a second body copy. A
  second H1 with different text is a legitimate layout and stays silent.

The warning is advisory, like its siblings. Unlike them it also covers terminal
cards, because it guards the record and a closed card's body is that record.
The message says to repair the card from the README's git history, or to fence
lines that are an example.

`Skill(refine-deck)` gained the rule in its core: edit a card's body, never its
whole README, and find a section by its line-anchored heading in the body. The
skill's size cap went from 15,300 to 15,700 bytes, with the rationale recorded
in `tests/test_skill_body_size.py`. `tests/test_validate_body_repeats_frontmatter.py`
also checks that the skill names the class the engine emits.

Related: [parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them](../parked-decision-cards-are-never-re-checked-against-the-code-that-moved-under-them/) (the same hygiene passes), [card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it](../card-frontmatter-passes-goc-validate-while-strict-yaml-parsers-reject-it/).
