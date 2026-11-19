---
title: goc-publish-releases-drafts-whose-dod-or-body-is-still-the-placeholder
summary: "goc publish refuses a draft only while both scaffold placeholders remain, so a draft with a real body but the placeholder DoD, or a real DoD but the placeholder body, publishes and enters goc --ready. The card-schema reference says publish has nothing to release until body and DoD are written, and publish's own refusal tells the author to write both. The ready queue then offers the autonomous loop cards with no closure contract or no briefing."
status: active
stage: null
contribution: medium
created: "2026-11-16T01:20:11Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, api-contract, documentation, unverified]
definition_of_done: |
  - [ ] EMPIRICAL: a `reproduce.py` runs the Falsification recipe (body-only and DoD-only drafts through `goc publish`, then `goc --ready`) on today's engine. Record the verdict in log.md and drop the `unverified` tag once it works.
  - [ ] TDD: if the hypothesis holds, `reproduce.py` exits 0 after the fix. `goc publish` exits 2 on a draft that still carries either placeholder and still releases a fully authored one. The fix may instead resolve the conflict the other way, with the reference and refusal text saying publish checks only for a pure placeholder; that choice and its reason go in log.md.
  - [ ] TDD: `tests/test_draft_guard_and_lifecycle.py` gains the two half-authored cases next to the existing all-placeholder and fully authored ones (`author()` at `:49` replaces both today).
  - [ ] MECHANICAL: `is_placeholder_scaffold`'s docstring (`goc/engine.py:2992-3002`), the refusal text (`:6901-6902`) and `Skill(card-schema)` reference.md § Draft contract (`:62-63`) state one rule, and plugin mirrors are re-synced.
worker: {who: "claude[bot]", where: main}
---

# `goc publish` releases drafts whose DoD or body is still the placeholder

Parked as `unverified`. A hunter agent reproduced it during an audit-deck run,
and the auditing agent reproduced it again by hand (output below), but there
is no `reproduce.py` yet.

## Hypothesis

`goc publish` refuses only a pure placeholder, a draft that still carries
*both* scaffold stubs (`goc/engine.py:3003-3005`):

```python
    dod = card.frontmatter.get("definition_of_done", "")
    dod_str = dod if isinstance(dod, str) else ""
    return SCAFFOLD_DOD_PLACEHOLDER in dod_str and SCAFFOLD_BODY_PLACEHOLDER in card.body
```

A draft with only one of the two authored passes. Three surfaces promise the
stricter rule:

- `Skill(card-schema)` reference.md § Draft contract (`:62-63`): publish
  "refuses on a pure placeholder (nothing to publish until body and DoD are
  written)".
- The refusal itself (`goc/engine.py:6901-6902`): "Write the card's real DoD
  and body before publishing it — `goc publish` releases authored work, it
  does not author it."
- `goc new`'s closing hint (`:7108`): "fill the body and DoD".

The predicate and the refusal both arrived in `e861360e`, which closed
[placeholder-cards-superseded-before-they-are-authored](../placeholder-cards-superseded-before-they-are-authored/).
In that commit the predicate was also described as a flagless backstop for
recognising legacy scaffolds. There, "both stubs present" is a safe sign of
"never authored", and the narrow test fits
([engine-comments-claim-unflagged-placeholder-cards-count-as-drafts](../engine-comments-claim-unflagged-placeholder-cards-count-as-drafts/)
corrected those comments). Its one consumer now is publish, which asks a
different question: "is this card authored?" No card records a decision that
half-authored drafts may be published.

## Falsification recipe

Run on 2026-11-16 against `main` at `ada1d2e7`, in a scratch repo:

1. Run `goc new body-only-card` and `goc new dod-only-card`.
2. In the first, replace only the body placeholder. In the second, replace
   only the DoD placeholder.
3. Run `goc publish <card> --no-commit` on each.
4. Run `goc --ready` and `goc validate`.

Observed:

```
--- goc publish body-only-card --no-commit:
body-only-card: published (draft flag cleared); now visible in the queue
exit=0
--- goc publish dod-only-card --no-commit:
dod-only-card: published (draft flag cleared); now visible in the queue
exit=0
--- goc --ready:
body-only-card  open    medium    3.0  none  bug   0/1
dod-only-card   open    medium    3.0  none  bug   0/1
--- goc validate:
WARN UNTAGGED_DOD_ITEM body-only-card: 1 DoD item(s) lack a method tag (TDD:/EMPIRICAL:/MECHANICAL:/PROCESS:): [- [ ] (replace with real criteria)]
exit=0
```

The hypothesis is falsified if publish exits 2 on either half-authored draft.

## Why it matters

The draft flag exists so that unauthored work cannot be acted on by
automation (reference.md § Draft contract). A published card with the
placeholder DoD is pullable at `human_gate: none` with no closure contract.
One with the placeholder body is pullable with no briefing. The only signal
is a non-fatal `UNTAGGED_DOD_ITEM` warning, and only in the DoD case. The
test helper `author()` (`tests/test_draft_guard_and_lifecycle.py:49`)
replaces both placeholders, so the suite covers only the two extremes.

## Why deferred

The audit round filed its own card and parked the hunter's other candidates;
there was no budget for a `reproduce.py`. The fix also has to pick a
direction. Either tighten the check to refuse while *either* placeholder
remains (code-suspect-first: three surfaces promise it), or keep the
pure-placeholder rule and correct the reference and refusal text. Gate left
at `none`: the surfaces agree on the stricter rule, so that is the default
unless the fixer finds a reason against it.

Surfaced by: the audit-deck hunter subagent (general-purpose, briefed on the
scheduler core: publish, claim, queue views).
