---
title: citation-repair-pass-declines-a-moved-function-whose-definition-line-gained-a-parameter
summary: "The citation anchor recipe relocates a defunct cite only on exact full-line equality, so any edit to the anchor line itself — a new keyword-only parameter, a changed return annotation, a reflowed signature — reads as 'anchor text absent' and the cite is declined for good even when the function it names is uniquely findable. Measured on this deck 2026-09-14: 12 declines across 9 open cards are def/class lines a unique-name match relocates, and one refactor adding a probe parameter to five install writers caused most of them."
status: active
stage: null
contribution: low
created: "2026-09-14T02:10:56Z"
closed_at: null
human_gate: none
advances: []
advanced_by: []
tags: [bug, documentation]
definition_of_done: |
  - [ ] TDD: `reproduce.py` exits zero — no decline over the open/active deck has a def/class anchor that a unique-name match locates.
  - [ ] MECHANICAL: `goc/templates/skills/refine-deck/reference.md` § "Citation anchor check" carries the definition-name relocation rule, stating both constraints (the range pair guard still decides emission; a non-unique name declines), and `SKILL.md`'s step 4 carries it in condensed form.
  - [ ] MECHANICAL: the residue table's `anchor text absent` row no longer tells the reader the code was refactored away as the only reading.
  - [ ] EMPIRICAL: the next `Skill(refine-deck)` pass after the rule lands repairs the 12 cites the transcript names, and its report shows the absent-decline count dropping by that amount.
worker: {who: "claude[bot]", where: main}
---

# Citation repair pass declines a moved function whose definition line gained a parameter

## Location

- `goc/templates/skills/refine-deck/reference.md` — § "Citation anchor check",
  the **Deciding** paragraph and the residue table under it. Mirrored to
  consumers at `.claude/skills/refine-deck/reference.md`,
  `claude-plugin/skills/…`, `codex-plugin/skills/…`, `openclaw-plugin/skills/…`.
- `goc/templates/skills/refine-deck/SKILL.md` — § "Defunct file:line
  citations", step 4 of the condensed recipe.

## What's broken

The relocate step matches by exact full-line equality:

> Then look for the anchor text in HEAD and rewrite the number only when the
> match is UNIQUE and the line is NON-TRIVIAL

That makes the anchor **line** the unit of identity. It is the right unit for
a statement inside a function body, where the line is all the card ever meant.
It is the wrong unit for a definition line, where the card means the *function*
and the line is only how the function announced itself on the day the cite was
written. Append a keyword-only parameter, widen a return annotation, or reflow
the argument list across two lines, and the function is still there, still
uniquely named, still one grep away — but the recipe reports `anchor text
absent` and declines. It will decline again on the next pass, and every pass
after, because nothing about the situation changes.

The recipe's residue table already reads this outcome as terminal:

> **anchor text absent** — the cited code was refactored away — re-read the
> card, and if the refactor also fixed the defect, close it per the core skill

For a renamed-signature function that advice is actively wrong. The code was
not refactored away; it grew a parameter. A reader who follows the instruction
looks for a defect that is still live and finds nothing at the address.

## Empirical evidence

`reproduce.py` replays the recipe over the open and active deck and reports the
declines whose anchor is a `def` or `class` line that a unique-name match
locates:

```
declines the exact-equality rule produces : 285
  ...whose anchor is a def/class line that a unique-name match locates : 12  over 9 cards

  engine.py:2457               start 2457 -> 2632   aggregation-epics-head-block-the-autonomous-pu
      anchored: def card_is_ready(card: Card, by_title: dict[str, Card]) -> bool:
      in HEAD : def card_is_ready(card: Card, by_title: dict[str, Card], *, include_drafts: bool = Fal
  goc/install.py:1258          start 1258 -> 1508   append-marker-block-matches-prose-mentions-of-
      anchored: def _append_marker_block(target: Path, block_body: str, *, header: str) -> None:
      in HEAD : def _append_marker_block(
  goc/install.py:1339-1361     start 1339 -> 1571   install-corrupts-pre-commit-config-in-the-styl
      anchored: def _append_precommit_hook(target: Path) -> None:
      in HEAD : def _append_precommit_hook(target: Path, *, probe: bool = False) -> bool:
  goc/install.py:1508-1538     start 1508 -> 1745   upgrade-divergence-report-marks-pristine-confi
      anchored: def _write_skills_source(target: Path, value: str) -> None:
      in HEAD : def _write_skills_source(target: Path, value: str, *, probe: bool = False) -> bool:
  …8 more
```

Every cite token above is a **dated record** of what the measurement found, not
an assertion about where code lives now, and is kept fenced so the recipe's own
scope rule classifies it correctly.

The distribution is the interesting part: **one refactor caused most of them.**
Five install-time writers — `_append_precommit_hook`, `_strip_claude_import`,
`_sync_claude_import`, `_write_skills_source`, and their callers — each gained
`*, probe: bool = False` when `_plan_upgrade_writes` was taught to ask an
executor whether it would change a file. Every card citing any of those
functions lost its anchor in one commit. That is the shape to expect: signature
drift arrives in families, so this decline class does not trickle in, it lands
in batches.

A wider relaxation would reach further — of the 55 non-trivial absent-anchor
declines this pass produced, 26 are recoverable by *some* relaxation (1 by
whitespace normalization, 10 by definition name, 15 by a 0.75 similarity
ratio). The definition-name subset is the one proposed here because it is the
only one with a principled identity claim behind it rather than a tuned
threshold.

## Why it matters

A decline is honest output, not silence, so this is a capability gap rather
than a correctness defect — it costs a reader a lookup, it does not mislead
them. But it is permanent and it compounds: these 12 cites will be declined by
every future pass, the population grows with each signature-touching refactor,
and 9 of the affected cards are gated at `human_gate: decision`, so the reader
who eventually picks them up is the one who pays.

Two siblings filed the same round, and the three interact:
[citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank](../citation-repair-pass-calls-a-cite-current-when-its-anchor-line-is-a-brace-or-blank/)
is the decide step accepting evidence it should refuse, this one is the relocate
step refusing evidence it should accept, and
[citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide](../citation-repair-pass-gives-two-cites-in-one-card-the-same-anchor-when-their-numbers-collide/)
is the anchor step attributing one cite's history to another. Both come from the same
root: the recipe states its substance guard once, in one place, and never asks
whether the same question arises at the other steps.

Earlier instances of that root, all closed, all on the relocate side:
[refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file](../refine-deck-citation-check-cannot-detect-line-drift-in-a-growing-file/),
[second-citation-repair-pass-moves-correct-cites-onto-unrelated-code](../second-citation-repair-pass-moves-correct-cites-onto-unrelated-code/),
[citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks](../citation-repair-pass-has-no-rule-for-cites-inside-fenced-code-blocks/),
[citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range](../citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range/).

## Fix

Add one relocation rule to `reference.md` § "Citation anchor check", after the
exact-match rule and before the residue table: when the anchor line is a `def`
or `class` definition and the exact text is absent, relocate on a unique match
of `def <name>(` / `class <name>(` instead. Same uniqueness requirement, same
refusal to guess — only the identity claim changes, from "this line" to "this
definition", which is what a cite naming a function meant in the first place.

Two constraints the rule has to carry, both already established by closed
cards in the family:

1. **The range pair guard still governs.** Seven of the twelve are range
   endpoints, and relocating a start while the end stays put is exactly the
   corruption
   [citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range](../citation-repair-pass-maps-range-endpoints-independently-and-corrupts-the-range/)
   closed. The name rule feeds the endpoint mapper; the pair check still
   decides whether the rewrite is emitted.
2. **A non-unique name is a decline, not a nearest match.** If two definitions
   share the name — an overload in a mirror tree, a method and a module-level
   function — report it as ambiguous and leave the number alone.

The residue table's `anchor text absent` row also needs its advice narrowed: it
should say the code may have been refactored away *or* may have moved with a
changed signature, so a reader does not read a decline as evidence the defect
is gone.

## Non-goals

- Whitespace-normalized or similarity-ratio matching. Both would reach further
  (16 more cites this round) and both rest on a tuned threshold rather than an
  identity claim; a wrong relocation is worse than a decline.
- Non-Python definition forms (TypeScript `function` / `const … =>`, shell
  functions). One in-scope cite this round would benefit; the rule can be
  widened when the evidence justifies it.
- Changing the addressing convention. That is the gated decision on
  [file-line-citations-drift-again-within-days-of-every-repair-pass](../file-line-citations-drift-again-within-days-of-every-repair-pass/).
