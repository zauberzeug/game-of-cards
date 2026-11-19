---
title: goc-publish-releases-drafts-whose-dod-or-body-is-still-the-placeholder
summary: "goc publish refused a draft only while both scaffold placeholders remained, so a draft with a real body but the placeholder DoD, or a real DoD but the placeholder body, published and entered goc --ready, against the card-schema reference and publish's own refusal text, which both say publish needs both written. Publish now refuses while either placeholder line remains and names the half that is left; a placeholder quoted inside a sentence does not count."
status: done
stage: null
contribution: medium
created: "2026-11-16T01:20:11Z"
closed_at: "2026-11-19T04:37:14Z"
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation]
definition_of_done: |
  - [x] EMPIRICAL: a `reproduce.py` runs the Falsification recipe (body-only and DoD-only drafts through `goc publish`, then `goc --ready`) on today's engine. Record the verdict in log.md and drop the `unverified` tag once it works.
  - [x] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix. `goc publish` exits 2 on a draft that still carries either placeholder and still releases a fully authored one. The fix may instead resolve the conflict the other way, with the reference and refusal text saying publish checks only for a pure placeholder; that choice and its reason go in log.md.
  - [x] TDD: `tests/test_draft_guard_and_lifecycle.py` gains the two half-authored cases next to the existing all-placeholder and fully authored ones (`author()` at `:50` now takes `dod=` / `body=` to leave one half as the placeholder).
  - [x] MECHANICAL: the predicate's docstring (`is_placeholder_scaffold`, renamed `scaffold_placeholders_left`, `goc/engine.py:3072-3101`), the refusal text (`:7151-7159`) and `Skill(card-schema)` reference.md § Draft contract (`:62-64`) state one rule, and plugin mirrors are re-synced.
worker: {who: "claude[bot]", where: main}
---

# `goc publish` releases drafts whose DoD or body is still the placeholder

Fixed: `goc publish` now refuses a draft while its DoD or its body still
holds the `goc new` placeholder line, and the refusal names the half that
is left. `reproduce.py` runs the Falsification recipe and exits 0.

## Location

- `goc/engine.py:3072` — `scaffold_placeholders_left` (was
  `is_placeholder_scaffold`), the predicate and its docstring.
- `goc/engine.py:7151-7159` — `_cmd_publish`'s refusal; `:7134-7141` its
  docstring; `:4811` the `publish` help line.
- `goc/templates/skills/card-schema/reference.md:60-66` — § Draft contract.
- `tests/test_draft_guard_and_lifecycle.py:103` and `:118` — the
  half-authored cases and the quoted-placeholder case.

## What was broken

`goc publish` refused only a pure placeholder, a draft that still carried
*both* scaffold stubs:

```python
    return SCAFFOLD_DOD_PLACEHOLDER in dod_str and SCAFFOLD_BODY_PLACEHOLDER in card.body
```

A draft with only one of the two authored passed. Three surfaces promised
the stricter rule: `Skill(card-schema)` reference.md § Draft contract
("nothing to publish until body and DoD are written"), the refusal itself
("Write the card's real DoD and body before publishing it") and `goc new`'s
closing hint ("fill the body and DoD").

The predicate and the refusal both arrived in `e861360e`, which closed
[placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/).
There the predicate was also a flagless backstop for recognising legacy
scaffolds, where "both stubs present" is a safe sign of "never authored"
([engine-comments-claim-unflagged-placeholder-cards-count-as-drafts](../engine-comments-claim-unflagged-placeholder-cards-count-as-drafts/)
corrected those comments). Its one consumer is now publish, which asks a
different question: "is this card authored?" No card recorded a decision
that half-authored drafts may be published.

## Why it mattered

The draft flag exists so that unauthored work cannot be acted on by
automation (reference.md § Draft contract). A published card with the
placeholder DoD is pullable at `human_gate: none` with no closure contract;
one with the placeholder body is pullable with no briefing. The only signal
was a non-fatal `UNTAGGED_DOD_ITEM` warning, and only in the DoD case. The
test helper `author()` replaced both placeholders, so the suite covered
only the two extremes.

## Falsification recipe

`reproduce.py`, in a scratch deck with every verb run `--no-commit`:

1. `goc new` three cards, each with `--summary` so the summary-release gate
   cannot be what refuses.
2. In `body-only-card` replace only the body placeholder, in
   `dod-only-card` only the DoD placeholder, in `authored-card` both.
3. `goc publish <card> --no-commit` on each, then `goc --ready`.

The defect fires when either half-authored draft publishes or is listed by
`goc --ready`. Exit 0 = defect gone (both refused with exit 2, both still
drafts, the authored control published and listed); exit 1 = defect fires.

Before the fix (`f109258e`) both half-authored drafts published with exit
0 and all three cards were listed by `goc --ready`. After it:

```
--- goc publish body-only-card --no-commit: exit=2
    ERROR: body-only-card: is still an unauthored scaffold (placeholder DoD). Write the card's real DoD and body before publishing it — `goc publish` releases authored work, it does not author it.
--- goc publish dod-only-card --no-commit: exit=2
    ERROR: dod-only-card: is still an unauthored scaffold (placeholder body). Write the card's real DoD and body before publishing it — `goc publish` releases authored work, it does not author it.
--- goc publish authored-card --no-commit: exit=0
--- goc --ready: authored-card only
```

## The rule now

A part counts as unwritten while one of its lines *is* the placeholder
line: the DoD item `- [ ] (replace with real criteria)` or the body line
`(write the design doc here)`. Publish refuses while either is left. Line
equality rather than a substring test keeps a card that quotes the
placeholder inside a sentence publishable, as
[placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/)
does; with one mention now enough to refuse, a substring test would have
turned every such quote into a refusal. A placeholder quoted alone on a
line still counts, as in the fenced reproducer output
[card-rename-leaves-old-title-in-body-and-skips-log-entry](../card-rename-leaves-old-title-in-body-and-skips-log-entry/)
carries. Publish refuses that loudly, naming the half, and the author can
reword it.

Claiming (`goc status <title> active`) and closing (`goc done`) still clear
the flag without this check: the claimer authors the card as part of
working it, and `goc done` refuses the unchecked placeholder DoD item on its
own.
